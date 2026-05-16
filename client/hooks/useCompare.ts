import { useState, useCallback } from "react";
import { compareSchemas } from "@/services/api";
import { SchemaComparisonRequest, ParseError, AnalysisResult } from "@/types/api";

export interface HistoryEntry {
    id: string;
    timestamp: string;
    risk_level: "LOW" | "MEDIUM" | "CRITICAL";
    score: number;
    tables_added: number;
    tables_modified: number;
    tables_deleted: number;
}

const HISTORY_STORAGE_KEY = "suture_deployment_history";

function saveToHistory(result: AnalysisResult) {
    try {
        const entry: HistoryEntry = {
            id: crypto.randomUUID(),
            timestamp: new Date().toISOString(),
            risk_level: result.blast_radius.risk_level,
            score: result.blast_radius.score,
            tables_added: result.changes_detected.summary.tables_added || 0,
            tables_modified: result.changes_detected.summary.tables_modified || 0,
            tables_deleted: result.changes_detected.summary.tables_deleted || 0,
        };

        const existingHistory = localStorage.getItem(HISTORY_STORAGE_KEY);
        const history: HistoryEntry[] = existingHistory ? JSON.parse(existingHistory) : [];

        history.unshift(entry);

        // Keep only the last 100 entries
        const trimmedHistory = history.slice(0, 100);

        localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(trimmedHistory));
    } catch (error) {
        console.error("Failed to save to history:", error);
    }
}

export function useCompare() {
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [parseErrors, setParseErrors] = useState<ParseError[]>([]);

    const executeCompare = useCallback(async (data: SchemaComparisonRequest) => {
        setLoading(true);
        setError(null);
        setParseErrors([]);
        setResult(null);
        try {
            const response = await compareSchemas(data);
            setResult(response);
            saveToHistory(response);
        } catch (error: any) {
            const errors: ParseError[] | undefined =
                error.errors && Array.isArray(error.errors)
                    ? error.errors
                    : error.response?.data?.detail?.errors;

            if (errors && Array.isArray(errors) && errors.length > 0) {
                setParseErrors(errors);
                setError(
                    error.message ||
                    error.response?.data?.detail?.message ||
                    "Failed to process schemas"
                );
            } else if (error.response?.data?.detail) {
                const detail = error.response.data.detail;
                setError(
                    typeof detail === "string"
                        ? detail
                        : detail.message || JSON.stringify(detail)
                );
            } else if (error.message) {
                setError(error.message);
            } else {
                setError("An unexpected error occurred.");
            }
        } finally {
            setLoading(false);
        }
    }, []);

    const resetCompare = useCallback(() => {
        setResult(null);
        setError(null);
        setLoading(false);
        setParseErrors([]);
    }, []);

    return {
        result,
        loading,
        error,
        parseErrors,
        executeCompare,
        resetCompare,
    };
}