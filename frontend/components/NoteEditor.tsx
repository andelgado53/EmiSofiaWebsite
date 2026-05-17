"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";

/**
 * Custom Image extension that adds a `float` attribute (`left` | `right`)
 * and renders with `class="note-photo note-photo--float-{float}"` and `alt=""`.
 */
const FloatImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      float: {
        default: null,
        parseHTML: (element) => {
          const classList = element.className || "";
          if (classList.includes("note-photo--float-left")) return "left";
          if (classList.includes("note-photo--float-right")) return "right";
          return null;
        },
        renderHTML: (attributes) => {
          const float = attributes.float as string | null;
          if (!float) {
            return { class: "note-photo", alt: "" };
          }
          return {
            class: `note-photo note-photo--float-${float}`,
            alt: "",
          };
        },
      },
    };
  },

  renderHTML({ HTMLAttributes }) {
    // Ensure alt is always empty string
    return ["img", { ...HTMLAttributes, alt: "" }];
  },
});

interface NoteEditorProps {
  content: string;
  onChange: (html: string) => void;
}

export default function NoteEditor({ content, onChange }: NoteEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      FloatImage,
    ],
    content,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
  });

  if (!editor) {
    return null;
  }

  return (
    <div className="border border-gray-300 rounded-lg overflow-hidden">
      {/* Toolbar */}
      <div className="flex flex-wrap gap-1 p-2 border-b border-gray-300 bg-gray-50">
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBold().run()}
          isActive={editor.isActive("bold")}
          label="Bold"
        >
          B
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleItalic().run()}
          isActive={editor.isActive("italic")}
          label="Italic"
        >
          I
        </ToolbarButton>
        <ToolbarButton
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 1 }).run()
          }
          isActive={editor.isActive("heading", { level: 1 })}
          label="Heading 1"
        >
          H1
        </ToolbarButton>
        <ToolbarButton
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 2 }).run()
          }
          isActive={editor.isActive("heading", { level: 2 })}
          label="Heading 2"
        >
          H2
        </ToolbarButton>
        <ToolbarButton
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 3 }).run()
          }
          isActive={editor.isActive("heading", { level: 3 })}
          label="Heading 3"
        >
          H3
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          isActive={editor.isActive("bulletList")}
          label="Bullet List"
        >
          • List
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          isActive={editor.isActive("orderedList")}
          label="Ordered List"
        >
          1. List
        </ToolbarButton>
      </div>

      {/* Editor content area */}
      <EditorContent
        editor={editor}
        className="prose max-w-none p-4 min-h-[200px] focus:outline-none"
      />
    </div>
  );
}

interface ToolbarButtonProps {
  onClick: () => void;
  isActive: boolean;
  label: string;
  children: React.ReactNode;
}

function ToolbarButton({
  onClick,
  isActive,
  label,
  children,
}: ToolbarButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-pressed={isActive}
      className={`px-2 py-1 text-sm font-medium rounded transition-colors ${
        isActive
          ? "bg-gray-800 text-white"
          : "bg-white text-gray-700 hover:bg-gray-200"
      }`}
    >
      {children}
    </button>
  );
}
