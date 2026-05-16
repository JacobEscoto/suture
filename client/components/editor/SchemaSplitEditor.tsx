'use client';

import React, { useState, memo } from "react";
import { SchemaComparisonRequest } from "@/types/api";

interface SchemaTextareaProps {
    label: string;
    value: string;
    onChange: (value: string) => void;
    placeholder: string;
}

function SchemaTextarea({ label, value, onChange, placeholder }: SchemaTextareaProps) {
    return (
        <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-zinc-400">
                {label}
            </label>
            <textarea
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder={placeholder}
                className="w-full h-96 p-4 rounded-xl bg-zinc-900 border border-zinc-800 text-zinc-100 font-mono text-sm focus:outline-none focus:border-indigo-500 transition-colors resize-none"
            />
        </div>
    );
}

interface SchemaSplitEditorProps {
    onCompare: (data: SchemaComparisonRequest) => void;
    isLoading: boolean;
}

const SchemaSplitEditor = memo(function SchemaSplitEditor({ onCompare, isLoading }: SchemaSplitEditorProps) {
    const [schemas, setSchemas] = useState({ v1: '', v2: '' });

    const handleSchemaChange = (key: 'v1' | 'v2', value: string) => {
        setSchemas((prev) => ({
            ...prev,
            [key]: value
        }));
    };

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

                <SchemaTextarea
                    label="Base Schema (Old SQL)"
                    value={schemas.v1}
                    onChange={(val) => handleSchemaChange('v1', val)}
                    placeholder="CREATE TABLE users (id SERIAL ...);"
                />

                <SchemaTextarea
                    label="Destination Schema (New SQL)"
                    value={schemas.v2}
                    onChange={(val) => handleSchemaChange('v2', val)}
                    placeholder="CREATE TABLE users (id SERIAL, email VARCHAR ...);"
                />

            </div>

            <div className="flex justify-center">
                <button
                    type="submit"
                    disabled={isLoading || !schemas.v1.trim() || !schemas.v2.trim()}
                    className="px-8 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white font-medium shadow-lg transition-all duration-200 cursor-pointer"
                >
                    {isLoading ? "Analyzing differences..." : "Suture Schemas"}
                </button>
            </div>
        </form>
    );
});

export default SchemaSplitEditor;