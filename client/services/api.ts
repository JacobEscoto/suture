import axios from "axios";
import { SchemaComparisonRequest, AnalysisResult } from "../types/api";

const api = axios.create({
    baseURL: "http://localhost:8000/api",
    headers: {
        'Content-Type': 'application/json',
    },
});

export const compareSchemas = async (data: SchemaComparisonRequest): Promise<AnalysisResult> => {
    try {
        const response = await api.post<AnalysisResult>("/compare", data);
        return response.data;
    } catch (error: any) {
        // Handle Axios errors
        if (error.response) {
            // FastAPI HTTPException returns error in 'detail' field
            const detail = error.response.data?.detail;

            // Handle different error formats
            if (typeof detail === 'string') {
                throw new Error(detail);
            } else if (Array.isArray(detail)) {
                // Validation errors (422) return array of error objects
                const errorMessages = detail.map((err: any) =>
                    `${err.loc?.join('.') || 'Field'}: ${err.msg}`
                ).join('; ');
                throw new Error(errorMessages);
            } else if (detail && typeof detail === 'object') {
                throw new Error(JSON.stringify(detail));
            } else {
                // Fallback for other response formats
                throw new Error(`Server error (${error.response.status}): ${error.response.statusText}`);
            }
        } else if (error.request) {
            // Request was made but no response received
            throw new Error("Error connecting to the Suturé server. Please ensure the server is running.");
        } else {
            // Something else happened
            throw new Error(error.message || "An unexpected error occurred");
        }
    }
};

export default api;