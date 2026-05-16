'use client';

import React, { useState, memo, useCallback } from "react";
import Editor from "react-simple-code-editor";
import { highlight, languages } from "prismjs";
import "prismjs/components/prism-sql";
import "prismjs/themes/prism-tomorrow.css";

import { Database, FileCode, Zap, Trash2 } from "lucide-react";
import { SchemaComparisonRequest } from "@/types/api";

interface SchemaCodeEditorProps {
    label: string;
    value: string;
    onChange: (value: string) => void;
    onClear: () => void;
    placeholder: string;
    icon: React.ReactNode;
}

function SchemaCodeEditor({ label, value, onChange, onClear, placeholder, icon }: SchemaCodeEditorProps) {
    return (
        <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-zinc-400 flex items-center gap-2">
                {icon}
                {label}
            </label>
            {value.trim() && (
                <button
                    type="button"
                    onClick={onClear}
                    className="text-xs text-zinc-500 hover:text-rose-400 transition-colors flex items-center gap-1 px-2 py-0.5 rounded hover:bg-rose-500/5 cursor-pointer"
                    title="Clear editor"
                >
                    <Trash2 className="w-3.5 h-3.5" />
                    Clear
                </button>
            )}
            <div className="w-full h-96 p-2 rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-100 font-mono text-sm focus-within:border-indigo-500 transition-colors overflow-y-auto">
                <Editor
                    value={value}
                    onValueChange={onChange}
                    highlight={(code) => highlight(code, languages.sql, "sql")}
                    padding={12}
                    placeholder={placeholder}
                    style={{
                        fontFamily: '"Fira code", "Fira Mono", monospace',
                        fontSize: 14,
                        minHeight: "100%",
                    }}
                    textareaClassName="focus:outline-none"
                />
            </div>
        </div>
    );
}

interface SchemaSplitEditorProps {
    onCompare: (data: SchemaComparisonRequest) => void;
    onReset?: () => void;
    isLoading: boolean;
}

const SchemaSplitEditor = memo(function SchemaSplitEditor({ onCompare, onReset, isLoading }: SchemaSplitEditorProps) {
    const [schemas, setSchemas] = useState({ v1: '', v2: '' });

    const handleSchemaChange = (key: 'v1' | 'v2', value: string) => {
        setSchemas((prev) => ({
            ...prev,
            [key]: value
        }));
    };

    const handleClearV1 = useCallback(() => {
        setSchemas((prev) => ({...prev, v1: ""}));
        if (onReset) {
            onReset();
        }
    }, [onReset]);

    const handleClearV2 = useCallback(() => {
        setSchemas((prev) => ({...prev, v2: ""}));
        if (onReset) {
            onReset();
        }
    }, [onReset]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!schemas.v1.trim() || !schemas.v2.trim()) {
            return;
        }
        onCompare({ schema_v1: schemas.v1, schema_v2: schemas.v2 });
    };

    return (
        <form onSubmit={handleSubmit} className="w-full flex flex-col gap-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                <SchemaCodeEditor
                    label="Base Schema (Old SQL)"
                    value={schemas.v1}
                    onChange={(val) => handleSchemaChange('v1', val)}
                    onClear={handleClearV1}
                    placeholder="CREATE TABLE users (id SERIAL ...);"
                    icon={<Database className="w-4 h-4 text-zinc-500" />}
                />

                <SchemaCodeEditor
                    label="Destination Schema (New SQL)"
                    value={schemas.v2}
                    onChange={(val) => handleSchemaChange('v2', val)}
                    onClear={handleClearV2}
                    placeholder="CREATE TABLE users (id SERIAL, email VARCHAR ...);"
                    icon={<FileCode className="w-4 h-4 text-indigo-400" />}
                />

            </div>

            <div className="flex justify-center">
                <button
                    type="submit"
                    disabled={isLoading || !schemas.v1.trim() || !schemas.v2.trim()}
                    className="px-8 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white font-medium shadow-lg transition-all duration-200 cursor-pointer flex items-center gap-2"
                >
                    <Zap className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                    {isLoading ? "Analyzing differences..." : "Suture Schemas"}
                </button>
            </div>
        </form>
    );
});

export default SchemaSplitEditor;