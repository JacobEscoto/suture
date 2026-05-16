import { useState, useCallback } from "react";
import { compareSchemas } from "@/services/api";
import { SchemaComparisonRequest, ParseError, AnalysisResult } from "@/types/api";

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
        } catch (error: any) {
            // Check if this is an Axios error with structured ParseError data
            if (error.response?.data?.detail) {
                const detail = error.response.data.detail;

                // Handle structured ParseError format
                if (detail.errors && Array.isArray(detail.errors)) {
                    setParseErrors(detail.errors);
                    setError(detail.message || "Failed to process schemas");
                } else if (typeof detail === 'string') {
                    // Simple string error
                    setError(detail);
                } else {
                    // Other structured error
                    setError(JSON.stringify(detail));
                }
            } else if (error.message) {
                // Plain Error object (from api.ts for connection errors, etc.)
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