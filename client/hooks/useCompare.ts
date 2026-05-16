import { useState, useCallback } from "react";
import { compareSchemas } from "@/services/api";
import { SchemaComparisonRequest, AnalysisResult } from "@/types/api";

export function useCompare() {
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const executeCompare = useCallback(async (data: SchemaComparisonRequest) => {
        setLoading(true);
        setError(null);
        try {
            const response = await compareSchemas(data);
            setResult(response);
        } catch (error: any) {
            setError(error.message || "An unexpected error ocurred while processing the schemas.");
            setResult(null);
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
        executeCompare,
        resetCompare,
    };
}