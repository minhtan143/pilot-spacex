"""KnowledgeGraphRepository — data access layer for the knowledge graph.

Provides upsert, traversal, hybrid search, and subgraph extraction for
graph nodes and edges. PostgreSQL-specific features (recursive CTEs,
pgvector) are guarded by dialect detection; SQLite falls back to
equivalent loop-based or keyword-only implementations for testing.

Feature 016: Knowledge Graph — Memory Engine replacement
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text

from pilot_space.domain.graph_edge import EdgeType, GraphEdge
from pilot_space.domain.graph_node import GraphNode, NodeType
from pilot_space.domain.graph_query import ScoredNode
from pilot_space.infrastructure.database.models.graph_edge import GraphEdgeModel
from pilot_space.infrastructure.database.models.graph_node import GraphNodeModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Score fusion weights
_EMBEDDING_WEIGHT = 0.5
_TEXT_WEIGHT = 0.2
_RECENCY_WEIGHT = 0.2
_SECONDS_PER_DAY = 86_400.0


# ---------------------------------------------------------------------------
# Module-level ORM→domain mappers (shared with _graph_search helpers)
# ---------------------------------------------------------------------------


def _node_model_to_domain(model: GraphNodeModel) -> GraphNode:
    """Map GraphNodeModel ORM to GraphNode domain object."""
    embedding: list[float] | None = None
    raw = model.embedding
    if raw is not None:
        if isinstance(raw, str):
            embedding = [float(v) for v in raw.strip("[]").split(",") if v.strip()]
        elif hasattr(raw, "__iter__"):
            embedding = list(raw)

    return GraphNode(
        id=model.id,
        workspace_id=model.workspace_id,
        node_type=NodeType(model.node_type),
        label=model.label,
        content=model.content or "",
        properties=dict(model.properties) if model.properties else {},
        embedding=embedding,
        user_id=model.user_id,
        external_id=model.external_id,
        created_at=model.created_at.replace(tzinfo=UTC)
        if model.created_at.tzinfo is None
        else model.created_at,
        updated_at=model.updated_at.replace(tzinfo=UTC)
        if model.updated_at.tzinfo is None
        else model.updated_at,
    )


def _edge_model_to_domain(model: GraphEdgeModel) -> GraphEdge:
    """Map GraphEdgeModel ORM to GraphEdge domain object."""
    created_at = model.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return GraphEdge(
        id=model.id,
        source_id=model.source_id,
        target_id=model.target_id,
        edge_type=EdgeType(model.edge_type),
        properties=dict(model.properties) if model.properties else {},
        weight=model.weight,
        created_at=created_at,
    )


async def _enrich_edge_density(
    session: AsyncSession,
    scored: list[ScoredNode],
) -> list[ScoredNode]:
    """Add edge_density_score to each ScoredNode.

    Counts both outgoing and incoming edges so target-only nodes are not
    penalised. Normalises by max_degree within the result set.
    """
    if not scored:
        return scored

    node_ids = [sn.node.id for sn in scored]
    out_result = await session.execute(
        select(GraphEdgeModel.source_id.label("node_id"), func.count().label("degree"))
        .where(GraphEdgeModel.source_id.in_(node_ids))
        .group_by(GraphEdgeModel.source_id)
    )
    in_result = await session.execute(
        select(GraphEdgeModel.target_id.label("node_id"), func.count().label("degree"))
        .where(GraphEdgeModel.target_id.in_(node_ids))
        .group_by(GraphEdgeModel.target_id)
    )
    degree_map: dict[UUID, int] = {}
    for row in out_result.fetchall():
        degree_map[row.node_id] = degree_map.get(row.node_id, 0) + row.degree
    for row in in_result.fetchall():
        degree_map[row.node_id] = degree_map.get(row.node_id, 0) + row.degree

    max_degree = max(degree_map.values(), default=1)
    return [
        ScoredNode(
            node=sn.node,
            score=sn.score,
            embedding_score=sn.embedding_score,
            text_score=sn.text_score,
            recency_score=sn.recency_score,
            edge_density_score=degree_map.get(sn.node.id, 0) / (max_degree + 1),
        )
        for sn in scored
    ]


async def _keyword_search(
    session: AsyncSession,
    query_text: str,
    workspace_id: UUID,
    node_types: list[NodeType] | None,
    limit: int,
) -> list[ScoredNode]:
    """SQLite-compatible LIKE keyword search."""
    pattern = f"%{query_text}%"
    conditions: list[Any] = [
        GraphNodeModel.workspace_id == workspace_id,
        GraphNodeModel.is_deleted == False,  # noqa: E712
        or_(GraphNodeModel.label.ilike(pattern), GraphNodeModel.content.ilike(pattern)),
    ]
    if node_types:
        conditions.append(GraphNodeModel.node_type.in_([str(nt) for nt in node_types]))

    stmt = (
        select(GraphNodeModel)
        .where(and_(*conditions))
        .order_by(GraphNodeModel.updated_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    models = result.scalars().all()

    now = datetime.now(tz=UTC)
    scored: list[ScoredNode] = []
    for model in models:
        updated = (
            model.updated_at.replace(tzinfo=UTC)
            if model.updated_at.tzinfo is None
            else model.updated_at
        )
        age_days = (now - updated).total_seconds() / _SECONDS_PER_DAY
        recency = 1.0 / (1.0 + age_days)
        scored.append(
            ScoredNode(
                node=_node_model_to_domain(model),
                score=_RECENCY_WEIGHT * recency + _TEXT_WEIGHT,
                embedding_score=0.0,
                text_score=1.0,
                recency_score=recency,
                edge_density_score=0.0,
            )
        )
    return await _enrich_edge_density(session, scored)


async def _hybrid_search_pg(
    session: AsyncSession,
    query_embedding: list[float],
    query_text: str,
    workspace_id: UUID,
    node_types: list[NodeType] | None,
    limit: int,
) -> list[ScoredNode]:
    """PostgreSQL hybrid search using pgvector cosine + ts_rank fusion."""
    embedding_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"
    type_filter = ""
    if node_types:
        type_list = ",".join(f"'{nt!s}'" for nt in node_types)
        type_filter = f"AND node_type IN ({type_list})"

    raw = text(f"""
        SELECT id,
            (1 - (embedding <=> CAST(:embedding AS vector(1536)))) AS embedding_score,
            COALESCE(ts_rank(
                to_tsvector('english', COALESCE(content,'') || ' ' || COALESCE(label,'')),
                plainto_tsquery('english', :query_text)
            ), 0.0) AS text_score,
            1.0 / (1.0 + EXTRACT(EPOCH FROM (NOW() - updated_at)) / :spd) AS recency_score
        FROM graph_nodes
        WHERE workspace_id = :workspace_id AND is_deleted = false
          AND embedding IS NOT NULL {type_filter}
        ORDER BY (
            :ew * (1 - (embedding <=> CAST(:embedding AS vector(1536))))
            + :tw * COALESCE(ts_rank(
                to_tsvector('english', COALESCE(content,'') || ' ' || COALESCE(label,'')),
                plainto_tsquery('english', :query_text)), 0.0)
            + :rw * (1.0 / (1.0 + EXTRACT(EPOCH FROM (NOW() - updated_at)) / :spd))
        ) DESC LIMIT :limit
    """)
    rows = await session.execute(
        raw,
        {
            "embedding": embedding_literal,
            "query_text": query_text,
            "workspace_id": str(workspace_id),
            "spd": _SECONDS_PER_DAY,
            "ew": _EMBEDDING_WEIGHT,
            "tw": _TEXT_WEIGHT,
            "rw": _RECENCY_WEIGHT,
            "limit": limit,
        },
    )
    row_maps = rows.mappings().all()
    if not row_maps:
        return []

    node_ids = [row["id"] for row in row_maps]
    model_result = await session.execute(
        select(GraphNodeModel).where(GraphNodeModel.id.in_(node_ids))
    )
    model_map: dict[UUID, GraphNodeModel] = {m.id: m for m in model_result.scalars().all()}

    scored: list[ScoredNode] = []
    for row in row_maps:
        model = model_map.get(row["id"])
        if model is None:
            continue
        emb, txt, rec = (
            float(row["embedding_score"]),
            float(row["text_score"]),
            float(row["recency_score"]),
        )
        scored.append(
            ScoredNode(
                node=_node_model_to_domain(model),
                score=_EMBEDDING_WEIGHT * emb + _TEXT_WEIGHT * txt + _RECENCY_WEIGHT * rec,
                embedding_score=emb,
                text_score=txt,
                recency_score=rec,
                edge_density_score=0.0,
            )
        )
    return await _enrich_edge_density(session, scored)


class KnowledgeGraphRepository:
    """Data access layer for knowledge graph nodes and edges.

    All methods are workspace-scoped. PostgreSQL-specific features
    (recursive CTE traversal, pgvector similarity) activate automatically;
    SQLite test environments fall back to BFS loops and LIKE keyword search.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async session."""
        self._session = session

    # Expose mappers as class attributes for external callers
    _model_to_domain = staticmethod(_node_model_to_domain)
    _edge_model_to_domain = staticmethod(_edge_model_to_domain)

    def _is_sqlite(self) -> bool:
        """Return True when the session is connected to SQLite."""
        bind = self._session.get_bind()
        return getattr(bind, "dialect", None) is not None and bind.dialect.name == "sqlite"

    # ------------------------------------------------------------------
    # Node upsert
    # ------------------------------------------------------------------

    async def upsert_node(self, node: GraphNode) -> GraphNode:
        """Idempotently persist a graph node.

        Matches by ``(workspace_id, node_type, external_id)`` when external_id
        is set; otherwise always inserts.
        """
        if node.external_id is not None:
            existing = await self._find_node_by_external(
                workspace_id=node.workspace_id,
                node_type=node.node_type,
                external_id=node.external_id,
            )
            if existing is not None:
                return await self._update_node_model(existing, node)
        return await self._insert_node(node)

    async def _find_node_by_external(
        self, workspace_id: UUID, node_type: NodeType, external_id: UUID
    ) -> GraphNodeModel | None:
        stmt = select(GraphNodeModel).where(
            GraphNodeModel.workspace_id == workspace_id,
            GraphNodeModel.node_type == str(node_type),
            GraphNodeModel.external_id == external_id,
            GraphNodeModel.is_deleted == False,  # noqa: E712
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def _insert_node(self, node: GraphNode) -> GraphNode:
        model = GraphNodeModel(
            id=node.id,
            workspace_id=node.workspace_id,
            node_type=str(node.node_type),
            label=node.label,
            content=node.content,
            properties=node.properties,
            embedding=node.embedding,
            user_id=node.user_id,
            external_id=node.external_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _node_model_to_domain(model)

    async def _update_node_model(self, model: GraphNodeModel, node: GraphNode) -> GraphNode:
        model.label = node.label
        model.content = node.content
        model.properties = node.properties
        if node.embedding is not None:
            model.embedding = node.embedding
        await self._session.flush()
        await self._session.refresh(model)
        return _node_model_to_domain(model)

    # ------------------------------------------------------------------
    # Edge upsert
    # ------------------------------------------------------------------

    async def upsert_edge(self, edge: GraphEdge) -> GraphEdge:
        """Idempotently persist an edge by (source_id, target_id, edge_type)."""
        stmt = select(GraphEdgeModel).where(
            GraphEdgeModel.source_id == edge.source_id,
            GraphEdgeModel.target_id == edge.target_id,
            GraphEdgeModel.edge_type == str(edge.edge_type),
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            existing.weight = edge.weight
            existing.properties = edge.properties
            await self._session.flush()
            await self._session.refresh(existing)
            return _edge_model_to_domain(existing)

        # Derive workspace_id from source node
        ws_result = await self._session.execute(
            select(GraphNodeModel.workspace_id).where(GraphNodeModel.id == edge.source_id)
        )
        workspace_id = ws_result.scalar_one()
        model = GraphEdgeModel(
            id=edge.id,
            source_id=edge.source_id,
            target_id=edge.target_id,
            workspace_id=workspace_id,
            edge_type=str(edge.edge_type),
            properties=edge.properties,
            weight=edge.weight,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _edge_model_to_domain(model)

    # ------------------------------------------------------------------
    # Neighbor traversal
    # ------------------------------------------------------------------

    async def get_neighbors(
        self,
        node_id: UUID,
        edge_types: list[EdgeType] | None = None,
        depth: int = 1,
    ) -> list[GraphNode]:
        """Return nodes reachable from node_id within depth hops.

        Uses recursive CTE on PostgreSQL; iterative BFS on SQLite.
        """
        if self._is_sqlite():
            return await self._get_neighbors_bfs(node_id, edge_types, depth)
        return await self._get_neighbors_cte(node_id, edge_types, depth)

    async def _get_neighbors_bfs(
        self, node_id: UUID, edge_types: list[EdgeType] | None, max_depth: int
    ) -> list[GraphNode]:
        visited: set[UUID] = {node_id}
        frontier: deque[UUID] = deque([node_id])
        result_ids: list[UUID] = []
        for _ in range(max_depth):
            if not frontier:
                break
            next_frontier: list[UUID] = []
            for current_id in frontier:
                for nid in await self._direct_neighbors(current_id, edge_types):
                    if nid not in visited:
                        visited.add(nid)
                        result_ids.append(nid)
                        next_frontier.append(nid)
            frontier = deque(next_frontier)
        if not result_ids:
            return []
        rows = await self._session.execute(
            select(GraphNodeModel).where(
                GraphNodeModel.id.in_(result_ids),
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
        return [_node_model_to_domain(m) for m in rows.scalars().all()]

    async def _direct_neighbors(
        self, node_id: UUID, edge_types: list[EdgeType] | None
    ) -> list[UUID]:
        """IDs of directly adjacent nodes (both directions)."""
        conditions_out: list[Any] = [GraphEdgeModel.source_id == node_id]
        conditions_in: list[Any] = [GraphEdgeModel.target_id == node_id]
        if edge_types:
            type_strs = [str(et) for et in edge_types]
            conditions_out.append(GraphEdgeModel.edge_type.in_(type_strs))
            conditions_in.append(GraphEdgeModel.edge_type.in_(type_strs))
        stmt = (
            select(GraphEdgeModel.target_id)
            .where(and_(*conditions_out))
            .union(select(GraphEdgeModel.source_id).where(and_(*conditions_in)))
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def _get_neighbors_cte(
        self, node_id: UUID, edge_types: list[EdgeType] | None, max_depth: int
    ) -> list[GraphNode]:
        """Recursive CTE traversal for PostgreSQL."""
        ef = ""
        if edge_types:
            ef = "AND edge_type IN (" + ",".join(f"'{et!s}'" for et in edge_types) + ")"
        raw = text(f"""
            WITH RECURSIVE neighbors(id, depth) AS (
                SELECT target_id, 1 FROM graph_edges WHERE source_id = :nid {ef}
                UNION ALL
                SELECT source_id, 1 FROM graph_edges WHERE target_id = :nid {ef}
                UNION ALL
                SELECT e.target_id, n.depth+1 FROM graph_edges e
                  JOIN neighbors n ON e.source_id = n.id WHERE n.depth < :md {ef}
                UNION ALL
                SELECT e.source_id, n.depth+1 FROM graph_edges e
                  JOIN neighbors n ON e.target_id = n.id WHERE n.depth < :md {ef}
            )
            SELECT DISTINCT gn.id FROM graph_nodes gn JOIN neighbors nb ON gn.id = nb.id
            WHERE gn.is_deleted = false AND gn.id != :nid
        """)
        rows = await self._session.execute(raw, {"nid": str(node_id), "md": max_depth})
        neighbor_ids = [row[0] for row in rows.fetchall()]
        if not neighbor_ids:
            return []
        result = await self._session.execute(
            select(GraphNodeModel).where(
                GraphNodeModel.id.in_(neighbor_ids),
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
        return [_node_model_to_domain(m) for m in result.scalars().all()]

    # ------------------------------------------------------------------
    # Hybrid search (delegates to module-level helpers)
    # ------------------------------------------------------------------

    async def hybrid_search(
        self,
        query_embedding: list[float] | None,
        query_text: str,
        workspace_id: UUID,
        node_types: list[NodeType] | None = None,
        limit: int = 10,
    ) -> list[ScoredNode]:
        """Hybrid vector + full-text + recency search.

        Falls back to keyword-only LIKE search on SQLite or when no embedding
        is provided. Fusion: 0.5 * embedding + 0.2 * text + 0.2 * recency.
        """
        if self._is_sqlite() or not query_embedding:
            return await _keyword_search(self._session, query_text, workspace_id, node_types, limit)
        return await _hybrid_search_pg(
            self._session, query_embedding, query_text, workspace_id, node_types, limit
        )

    # ------------------------------------------------------------------
    # Subgraph extraction
    # ------------------------------------------------------------------

    async def get_subgraph(
        self,
        root_id: UUID,
        max_depth: int = 2,
        max_nodes: int = 50,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """BFS subgraph rooted at root_id, capped at max_nodes.

        Pruning priority: root first, then degree DESC, then recency DESC.
        """
        visited: set[UUID] = {root_id}
        frontier: list[UUID] = [root_id]
        all_ids: list[UUID] = [root_id]
        for _ in range(max_depth):
            if not frontier:
                break
            next_frontier: list[UUID] = []
            for current_id in frontier:
                for nid in await self._direct_neighbors(current_id, None):
                    if nid not in visited:
                        visited.add(nid)
                        all_ids.append(nid)
                        next_frontier.append(nid)
            frontier = next_frontier

        if len(all_ids) > max_nodes:
            all_ids = await self._prioritize_nodes(all_ids, root_id, max_nodes)

        node_result = await self._session.execute(
            select(GraphNodeModel).where(
                GraphNodeModel.id.in_(all_ids),
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
        nodes = [_node_model_to_domain(m) for m in node_result.scalars().all()]
        edge_result = await self._session.execute(
            select(GraphEdgeModel).where(
                GraphEdgeModel.source_id.in_(all_ids),
                GraphEdgeModel.target_id.in_(all_ids),
            )
        )
        edges = [_edge_model_to_domain(m) for m in edge_result.scalars().all()]
        return nodes, edges

    async def _prioritize_nodes(
        self, node_ids: list[UUID], root_id: UUID, max_nodes: int
    ) -> list[UUID]:
        degree_result = await self._session.execute(
            select(GraphEdgeModel.source_id.label("node_id"), func.count().label("cnt"))
            .where(
                or_(GraphEdgeModel.source_id.in_(node_ids), GraphEdgeModel.target_id.in_(node_ids))
            )
            .group_by(GraphEdgeModel.source_id)
        )
        degree_map: dict[UUID, int] = {row.node_id: row.cnt for row in degree_result.fetchall()}
        models = {
            m.id: m
            for m in (
                await self._session.execute(
                    select(GraphNodeModel).where(GraphNodeModel.id.in_(node_ids))
                )
            )
            .scalars()
            .all()
        }

        def _sort_key(nid: UUID) -> tuple[int, int, float]:
            model = models.get(nid)
            updated = model.updated_at if model else datetime.min.replace(tzinfo=UTC)
            return (0 if nid == root_id else 1, -degree_map.get(nid, 0), -updated.timestamp())

        return sorted(node_ids, key=_sort_key)[:max_nodes]

    # ------------------------------------------------------------------
    # User context
    # ------------------------------------------------------------------

    async def get_user_context(
        self,
        user_id: UUID,
        workspace_id: UUID,
        limit: int = 10,
    ) -> list[GraphNode]:
        """Recent nodes scoped to a user or belonging to their workspace."""
        stmt = (
            select(GraphNodeModel)
            .where(
                GraphNodeModel.workspace_id == workspace_id,
                GraphNodeModel.is_deleted == False,  # noqa: E712
                or_(
                    GraphNodeModel.user_id == user_id,
                    GraphNodeModel.user_id == None,  # noqa: E711
                ),
            )
            .order_by(GraphNodeModel.updated_at.desc())
            .limit(limit)
        )
        return [
            _node_model_to_domain(m) for m in (await self._session.execute(stmt)).scalars().all()
        ]

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    async def bulk_upsert_nodes(self, nodes: list[GraphNode]) -> list[GraphNode]:
        """Batch upsert; delegates to upsert_node for each entry."""
        return [await self.upsert_node(node) for node in nodes]

    # ------------------------------------------------------------------
    # Soft-delete expiry
    # ------------------------------------------------------------------

    async def delete_expired_nodes(self, before: datetime) -> int:
        """Soft-delete stale unpinned nodes with updated_at < before.

        Returns count of nodes soft-deleted.
        """
        result = await self._session.execute(
            select(GraphNodeModel).where(
                GraphNodeModel.updated_at < before,
                GraphNodeModel.is_deleted == False,  # noqa: E712
            )
        )
        candidates = result.scalars().all()
        now = datetime.now(tz=UTC)
        count = 0
        for model in candidates:
            if (model.properties or {}).get("pinned"):
                continue
            model.is_deleted = True
            model.deleted_at = now
            count += 1
        if count:
            await self._session.flush()
        return count


__all__ = ["KnowledgeGraphRepository"]
