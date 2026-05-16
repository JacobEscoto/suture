'use client';

import React, { useState, memo, useCallback, useRef, useEffect } from "react";
import Editor from "react-simple-code-editor";
import { highlight, languages } from "prismjs";
import "prismjs/components/prism-sql";
import "prismjs/themes/prism-tomorrow.css";

import { Database, FileCode, Zap, Trash2, AlertTriangle } from "lucide-react";
import { SchemaComparisonRequest, ParseError } from "@/types/api";

interface SchemaCodeEditorProps {
    label: string;
    value: string;
    onChange: (value: string) => void;
    onClear: () => void;
    placeholder: string;
    icon: React.ReactNode;
    error?: ParseError | null;
    isValidating?: boolean;
}

function SchemaCodeEditor({
    label, value, onChange, onClear, placeholder, icon, error, isValidating
}: SchemaCodeEditorProps) {
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
            <div className={`w-full h-96 p-2 rounded-xl bg-zinc-900 border text-zinc-100 font-mono text-sm transition-colors overflow-y-auto ${
                error ? 'border-rose-500 focus-within:border-rose-400' : 'border-zinc-800 focus-within:border-indigo-500'
            }`}>
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

            {isValidating && (
                <div className="text-xs text-zinc-500 flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></div>
                    Validating...
                </div>
            )}

            {error && (
                <div className="bg-rose-500/10 border border-rose-500/20 rounded-lg p-3 animate-fade-in">
                    <div className="flex items-start gap-2">
                        <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs font-bold text-rose-400 uppercase tracking-wider">
                                    Syntax Error
                                    {error.line_number && ` at Line ${error.line_number}`}
                                </span>
                            </div>
                            <p className="text-sm text-rose-300/90 mb-2">{error.message}</p>
                            {error.suggestion && (
                                <div className="flex items-start gap-2 text-xs text-amber-400 bg-amber-500/10 p-2 rounded border border-amber-500/20">
                                    <span className="font-bold">💡 Suggestion:</span>
                                    <span>{error.suggestion}</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

interface SchemaSplitEditorProps {
    onCompare: (data: SchemaComparisonRequest) => void;
    onReset?: () => void;
    isLoading: boolean;
    parseErrors?: ParseError[];
}

const SchemaSplitEditor = memo(function SchemaSplitEditor({
    onCompare, onReset, isLoading, parseErrors
}: SchemaSplitEditorProps) {
    const [schemas, setSchemas] = useState({ v1: '', v2: '' });
    const [isValidating, setIsValidating] = useState(false);
    const debounceTimer = useRef<NodeJS.Timeout | null>(null);

    const handleSchemaChange = (key: 'v1' | 'v2', value: string) => {
        setSchemas((prev) => ({
            ...prev,
            [key]: value
        }));

        // Trigger live validation if BOTH schemas have content
        if (schemas.v1.trim() && schemas.v2.trim()) {
            triggerLiveValidation(key === 'v1' ? value : schemas.v1, key === 'v2' ? value : schemas.v2);
        }
    };

    const triggerLiveValidation = useCallback((v1: string, v2: string) => {
        // Clear previous timer
        if (debounceTimer.current) {
            clearTimeout(debounceTimer.current);
        }

        setIsValidating(true);

        // Debounce: wait 800ms before validating
        debounceTimer.current = setTimeout(() => {
            if (v1.trim() && v2.trim()) {
                onCompare({ schema_v1: v1, schema_v2: v2 });
            }
            setIsValidating(false);
        }, 800);
    }, [onCompare]);

    useEffect(() => {
        return () => {
            if (debounceTimer.current) {
                clearTimeout(debounceTimer.current);
            }
        };
    }, []);

    const handleClearV1 = useCallback(() => {
        setSchemas((prev) => ({...prev, v1: ""}));
        if (debounceTimer.current) {
            clearTimeout(debounceTimer.current);
        }
        setIsValidating(false);
        if (onReset) {
            onReset();
        }
    }, [onReset]);

    const handleClearV2 = useCallback(() => {
        setSchemas((prev) => ({...prev, v2: ""}));
        if (debounceTimer.current) {
            clearTimeout(debounceTimer.current);
        }
        setIsValidating(false);
        if (onReset) {
            onReset();
        }
    }, [onReset]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!schemas.v1.trim() || !schemas.v2.trim()) {
            return;
        }
        // Cancel live validation timer and run immediate validation
        if (debounceTimer.current) {
            clearTimeout(debounceTimer.current);
        }
        setIsValidating(false);
        onCompare({ schema_v1: schemas.v1, schema_v2: schemas.v2 });
    };

    // Find errors for each editor
    const v1Error = parseErrors?.find(err => err.editor === 'v1');
    const v2Error = parseErrors?.find(err => err.editor === 'v2');

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
                    error={v1Error}
                    isValidating={isValidating}
                />

                <SchemaCodeEditor
                    label="Destination Schema (New SQL)"
                    value={schemas.v2}
                    onChange={(val) => handleSchemaChange('v2', val)}
                    onClear={handleClearV2}
                    placeholder="CREATE TABLE users (id SERIAL, email VARCHAR ...);"
                    icon={<FileCode className="w-4 h-4 text-indigo-400" />}
                    error={v2Error}
                    isValidating={isValidating}
                />

            </div>

            <div className="flex justify-center">
                <button
                    type="submit"
                    disabled={isLoading || isValidating || !schemas.v1.trim() || !schemas.v2.trim()}
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