# Suturé Frontend Enhancement - Advanced Features

This document covers advanced features including editor integration, error highlighting, and real-time validation.

---

## Phase 4: Enhanced Error Handling

### Step 4.1: Update ErrorAlert Component

**File:** `client/components/layout/ErrorAlert.tsx`

Replace entire file with enhanced error display:

```typescript
'use client';

import React from 'react';
import { AlertCircle, X } from 'lucide-react';
import { ParseError } from '@/types/api';

interface ErrorAlertProps {
  message?: string;
  errors?: ParseError[];
  onDismiss?: () => void;
}

export default function ErrorAlert({ message, errors, onDismiss }: ErrorAlertProps) {
  if (!message && (!errors || errors.length === 0)) return null;

  return (
    <div className="w-full bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 animate-fade-in">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-rose-400 mb-2">Error Processing Schemas</h3>

          {message && (
            <p className="text-sm text-rose-300/80 mb-3">{message}</p>
          )}

          {errors && errors.length > 0 && (
            <div className="space-y-3">
              {errors.map((error, idx) => (
                <div key={idx} className="bg-zinc-900/50 rounded-lg p-3 border border-rose-500/10">
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider">
                      {error.editor === 'v1' ? 'Base Schema' : 'Destination Schema'}
                      {error.line_number && ` (Line ${error.line_number})`}
                    </span>
                    <span className="text-[10px] text-zinc-500 uppercase">{error.error_type}</span>
                  </div>

                  <p className="text-sm text-rose-300/90 mb-2">{error.message}</p>

                  {error.statement && (
                    <div className="bg-zinc-950 rounded p-2 mb-2">
                      <code className="text-xs text-zinc-400 font-mono">{error.statement}</code>
                    </div>
                  )}

                  {error.suggestion && (
                    <div className="flex items-start gap-2 text-xs text-amber-400">
                      <span className="font-semibold">Suggestion:</span>
                      <span>{error.suggestion}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-rose-400 hover:text-rose-300 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
```

### Step 4.2: Update useCompare Hook

**File:** `client/hooks/useCompare.ts`

Add support for structured errors:

```typescript
import { useState, useCallback } from "react";
import { compareSchemas } from "@/services/api";
import { SchemaComparisonRequest, AnalysisResult, ParseError } from "@/types/api";

export function useCompare() {
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [parseErrors, setParseErrors] = useState<ParseError[]>([]);

    const executeCompare = useCallback(async (data: SchemaComparisonRequest) => {
        setLoading(true);
        setError(null);
        setParseErrors([]);

        try {
            const response = await compareSchemas(data);
            setResult(response);

            // Check for errors in response
            if (response.errors && response.errors.length > 0) {
                setParseErrors(response.errors);
            }
        } catch (error: any) {
            // Check if error has structured parse errors
            if (error.response?.data?.errors) {
                setParseErrors(error.response.data.errors);
                setError(error.response.data.message || "Failed to process schemas");
            } else {
                setError(error.message || "An unexpected error occurred while processing the schemas.");
            }
            setResult(null);
        } finally {
            setLoading(false);
        }
    }, []);

    const resetCompare = useCallback(() => {
        setResult(null);
        setError(null);
        setParseErrors([]);
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
```

### Step 4.3: Update Main Page

**File:** `client/app/page.tsx`

Update to use parseErrors:

```typescript
export default function Home() {
  const { result, loading, error, parseErrors, executeCompare } = useCompare();

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-50 flex flex-col">
      <AppNavigation />

      <section className="flex-1 max-w-7xl w-full mx-auto px-4 py-12 flex flex-col gap-8">
        <HeroSection />

        <div className="w-full bg-zinc-900/30 border border-zinc-900/80 rounded-2xl p-6 shadow-2xl backdrop-blur-sm">
          <SchemaSplitEditor onCompare={executeCompare} isLoading={loading} />
        </div>

        {(error || parseErrors.length > 0) && (
          <ErrorAlert message={error || undefined} errors={parseErrors} />
        )}

        {result && (
          <div className="w-full border-t border-zinc-900 pt-4">
            <ComparisonResults result={result} />
          </div>
        )}
      </section>

      <AppFooter />
    </main>
  );
}
```

---

## Phase 5: Advanced Editor Features (Future Enhancement)

### Option 1: Monaco Editor Integration

For advanced diff visualization, consider replacing `react-simple-code-editor` with Monaco Editor:

**Installation:**
```bash
npm install @monaco-editor/react
```

**Example Implementation:**

```typescript
'use client';

import React from 'react';
import Editor from '@monaco-editor/react';

interface MonacoDiffEditorProps {
  original: string;
  modified: string;
  language?: string;
}

export default function MonacoDiffEditor({
  original,
  modified,
  language = 'sql'
}: MonacoDiffEditorProps) {
  return (
    <Editor
      height="400px"
      language={language}
      theme="vs-dark"
      original={original}
      modified={modified}
      options={{
        readOnly: true,
        renderSideBySide: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 14,
        lineNumbers: 'on',
        glyphMargin: true,
        folding: true,
        lineDecorationsWidth: 10,
        lineNumbersMinChars: 3,
      }}
    />
  );
}
```

### Option 2: Error Markers in Editors

Add visual error indicators in the code editors:

```typescript
interface EditorMarker {
  startLineNumber: number;
  endLineNumber: number;
  startColumn: number;
  endColumn: number;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

// In Monaco Editor
const markers: EditorMarker[] = parseErrors
  .filter(err => err.line_number)
  .map(err => ({
    startLineNumber: err.line_number!,
    endLineNumber: err.line_number!,
    startColumn: err.column_number || 1,
    endColumn: err.column_number ? err.column_number + 10 : 100,
    message: err.message,
    severity: 'error' as const,
  }));

monaco.editor.setModelMarkers(model, 'sql-parser', markers);
```

### Option 3: Real-Time Validation

Implement debounced validation as users type:

```typescript
import { useEffect, useRef } from 'react';
import { debounce } from 'lodash';

function useRealtimeValidation(sql: string, onValidate: (errors: ParseError[]) => void) {
  const validateRef = useRef(
    debounce(async (sqlContent: string) => {
      try {
        // Call a validation-only endpoint
        const response = await fetch('/api/validate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sql: sqlContent }),
        });
        const data = await response.json();
        onValidate(data.errors || []);
      } catch (error) {
        console.error('Validation error:', error);
      }
    }, 500)
  );

  useEffect(() => {
    if (sql.trim()) {
      validateRef.current(sql);
    }
  }, [sql]);
}
```

---

## Phase 6: UI/UX Polish

### Step 6.1: Add Animations

**File:** `client/app/globals.css`

Add custom animations:

```css
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 0 0 5px rgba(34, 197, 94, 0.3);
  }
  50% {
    box-shadow: 0 0 20px rgba(34, 197, 94, 0.6);
  }
}

.animate-fade-in {
  animation: fade-in 0.3s ease-out;
}

.animate-pulse-glow {
  animation: pulse-glow 2s ease-in-out infinite;
}
```

### Step 6.2: Add Loading States

**File:** `client/components/results/ComparisonResults.tsx`

Add skeleton loading:

```typescript
function LoadingSkeleton() {
  return (
    <div className="w-full flex flex-col gap-8 mt-8 animate-pulse">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 h-24" />
        ))}
      </div>
      <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6 h-48" />
      <div className="bg-zinc-950 rounded-xl border border-zinc-800 h-96" />
    </div>
  );
}
```

### Step 6.3: Add Tooltips

Install a tooltip library:

```bash
npm install @radix-ui/react-tooltip
```

**Example usage:**

```typescript
import * as Tooltip from '@radix-ui/react-tooltip';

<Tooltip.Provider>
  <Tooltip.Root>
    <Tooltip.Trigger asChild>
      <span className="cursor-help underline decoration-dotted">
        {column.data_type}
      </span>
    </Tooltip.Trigger>
    <Tooltip.Portal>
      <Tooltip.Content
        className="bg-zinc-800 text-zinc-100 px-3 py-2 rounded-lg text-xs max-w-xs"
        sideOffset={5}
      >
        <div className="space-y-1">
          <div className="font-semibold">Data Type Change</div>
          <div className="text-zinc-400">
            Changing from {column.old_data_type} to {column.data_type} may require data casting.
          </div>
        </div>
        <Tooltip.Arrow className="fill-zinc-800" />
      </Tooltip.Content>
    </Tooltip.Portal>
  </Tooltip.Root>
</Tooltip.Provider>
```

---

## Phase 7: Performance Optimization

### Step 7.1: Lazy Loading for Large Results

```typescript
import dynamic from 'next/dynamic';

const TableChangeCard = dynamic(() => import('./TableChangeCard'), {
  loading: () => <div className="h-16 bg-zinc-900 rounded-xl animate-pulse" />,
});
```

### Step 7.2: Virtual Scrolling for Many Tables

For schemas with hundreds of tables, implement virtual scrolling:

```bash
npm install react-window
```

```typescript
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={changes_detected.tables.length}
  itemSize={80}
  width="100%"
>
  {({ index, style }) => (
    <div style={style}>
      <TableChangeCard table={changes_detected.tables[index]} />
    </div>
  )}
</FixedSizeList>
```

### Step 7.3: Memoization

Optimize re-renders with React.memo and useMemo:

```typescript
const sortedTables = useMemo(() => {
  return [...changes_detected.tables].sort((a, b) => {
    const priority = { deleted: 0, modified: 1, added: 2 };
    return priority[a.change_type] - priority[b.change_type];
  });
}, [changes_detected.tables]);
```

---

## Summary of Key Improvements

### 1. Data Utilization
- **Before:** 10% of backend data displayed
- **After:** 90%+ of backend data displayed with full details

### 2. User Experience
- **Before:** "users (modified)" with no details
- **After:** Expandable cards showing all column, constraint, and index changes with before/after comparison

### 3. Error Handling
- **Before:** Generic error messages
- **After:** Line-specific errors with suggestions and visual highlighting

### 4. Visual Feedback
- **Before:** Static badges
- **After:** Animated indicators, risk levels, warnings, and rich tooltips

### 5. Migration Safety
- **Before:** No warnings about data loss
- **After:** Explicit warnings for destructive operations with risk assessment

---

## Implementation Priority

### Phase 1 (Critical - Must Do First)
1. ✅ Backend API enhancement to send complete data
2. ✅ Frontend type definitions update
3. ✅ TableChangeCard component creation
4. ✅ ComparisonResults update
5. ✅ Enhanced error handling

### Phase 2 (High Priority)
6. Add warnings display
7. Update error alert component
8. Test with real schema changes

### Phase 3 (Medium Priority - Future)
9. Monaco Editor integration for diff view
10. Real-time validation
11. Tooltips and animations

### Phase 4 (Low Priority - Polish)
12. Performance optimizations
13. Virtual scrolling
14. Advanced animations

---

## Testing Checklist

- [ ] Backend sends complete column details
- [ ] Backend sends complete constraint details
- [ ] Backend sends complete index details
- [ ] Backend generates appropriate warnings
- [ ] Frontend displays expandable table cards
- [ ] Frontend shows before/after column comparisons
- [ ] Frontend displays constraint changes
- [ ] Frontend displays index changes
- [ ] Frontend shows warnings prominently
- [ ] Error messages include line numbers
- [ ] Error messages include suggestions
- [ ] Error messages identify which editor has the error
- [ ] UI is responsive on mobile devices
- [ ] Performance is acceptable with 50+ tables
- [ ] Animations are smooth and not distracting

---

## Next Steps

1. **Start with Phase 1** - Backend changes are critical and must be done first
2. **Test incrementally** - Test each component as you build it
3. **Gather feedback** - Show users the enhanced UI and iterate
4. **Monitor performance** - Ensure the app remains fast with large schemas
5. **Document changes** - Update user documentation with new features

For questions or clarifications, refer to ARCHITECTURAL_REVIEW.md for the full context.