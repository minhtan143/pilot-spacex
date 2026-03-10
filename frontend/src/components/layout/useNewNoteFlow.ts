'use client';

/**
 * useNewNoteFlow - Encapsulates TemplatePicker + project-selector state for the "New Note" flow.
 *
 * Returns state, handlers, and props needed to render the two-step modal sequence.
 */
import { useState, useCallback } from 'react';
import type { NoteTemplate } from '@/services/api/templates';
import type { JSONContent } from '@/types';

interface UseNewNoteFlowOptions {
  onCreateNote: (data: { title: string; content: JSONContent; projectId?: string }) => void;
}

export function useNewNoteFlow({ onCreateNote }: UseNewNoteFlowOptions) {
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const [pendingTemplate, setPendingTemplate] = useState<NoteTemplate | null | undefined>(
    undefined
  );
  const [showProjectPicker, setShowProjectPicker] = useState(false);

  const open = useCallback(() => {
    setShowTemplatePicker(true);
  }, []);

  const handleTemplateConfirm = useCallback((template: NoteTemplate | null) => {
    setShowTemplatePicker(false);
    setPendingTemplate(template);
    setShowProjectPicker(true);
  }, []);

  const handleTemplateClose = useCallback(() => {
    setShowTemplatePicker(false);
  }, []);

  const handleProjectSelect = useCallback(
    (projectId: string | null) => {
      setShowProjectPicker(false);
      const template = pendingTemplate;
      setPendingTemplate(undefined);
      onCreateNote({
        title: template ? `New ${template.name} Note` : 'Untitled',
        content: (template?.content ?? { type: 'doc', content: [{ type: 'paragraph' }] }) as JSONContent,
        ...(projectId ? { projectId } : {}),
      });
    },
    [pendingTemplate, onCreateNote]
  );

  const handleProjectClose = useCallback(() => {
    setShowProjectPicker(false);
    setPendingTemplate(undefined);
  }, []);

  return {
    showTemplatePicker,
    showProjectPicker,
    handleTemplateConfirm,
    handleTemplateClose,
    handleProjectSelect,
    handleProjectClose,
    open,
  };
}
