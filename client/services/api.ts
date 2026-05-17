import axios from "axios";
import { SchemaComparisonRequest, AnalysisResult, ValidationResult } from "../types/api";

const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const compareSchemas = async (data: SchemaComparisonRequest): Promise<AnalysisResult> => {
    try {
        const response = await api.post<AnalysisResult>("/compare", data);
        return response.data;
    } catch (error: any) {
        if (error.response) {
            const detail = error.response.data?.detail;

            if (detail && typeof detail === 'object' && detail.errors) {
                const parseError = new Error(detail.message || "SQL Parse Error");
                (parseError as any).errors = detail.errors;
                (parseError as any).response = error.response;
                throw parseError;
            }

            if (detail && typeof detail === 'object' && detail.message) {
                throw new Error(detail.message);
            }

            if (Array.isArray(detail)) {
                const errorMessages = detail
                    .map((err: any) => `${err.loc?.join('.') || 'Field'}: ${err.msg}`)
                    .join('; ');
                throw new Error(errorMessages);
            }

            if (typeof detail === 'string') {
                throw new Error(detail);
            }

            throw new Error(`Server error (${error.response.status}): ${error.response.statusText}`);
        }

        if (error.request) {
            throw new Error("Error connecting to the Suturé server. Please ensure the server is running.");
        }

        throw new Error(error.message || "An unexpected error occurred");
    }
};

export const validateSqlMigration = async (data: SchemaComparisonRequest): Promise<ValidationResult> => {
    try {
        const response = await api.post<ValidationResult>("/validate", data);
        return response.data;
    } catch (error: any) {
        if (error.response) {
            const detail = error.response.data?.detail;

            if (detail && typeof detail === 'string') {
                throw new Error(detail);
            }

            throw new Error(`Server error (${error.response.status}): ${error.response.statusText}`);
        }

        if (error.request) {
            throw new Error("Error connecting to the Suturé server. Please ensure the server is running.");
        }

        throw new Error(error.message || "An unexpected error occurred");
    }
};

export default api;