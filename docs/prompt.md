_⚠️ Potential issue_

**Replace placeholder auth with real dependency.**

Hardcoded demo user violates security guidelines; implement proper auth or return 401/501 until ready.

Example minimal API key guard (illustrative):

```diff
-from fastapi import APIRouter, HTTPException, Depends
+from fastapi import APIRouter, HTTPException, Depends, Security, status
+from fastapi.security import APIKeyHeader
...
-# TODO 04: Add proper authentication dependency
-async def get_current_user():
-    """Get current authenticated user - placeholder implementation."""
-    return {"user_id": "demo_user", "tenant_id": "demo_tenant"}
+api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
+
+async def get_current_user(api_key: str = Security(api_key_header)):
+    """Simple API key auth; replace with real auth provider."""
+    if not api_key:
+        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
+    # TODO: validate api_key and resolve user/tenant
+    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Authentication not implemented")
```

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
from fastapi import APIRouter, HTTPException, Depends, Security, status
from fastapi.security import APIKeyHeader
...
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_current_user(api_key: str = Security(api_key_header)):
    """Simple API key auth; replace with real auth provider."""
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    # TODO: validate api_key and resolve user/tenant
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Authentication not implemented")
```

</details>

<!-- suggestion_end -->

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In backend/app/api/routes/agents.py around lines 78 to 82, the get_current_user
function returns a hardcoded demo user; replace this placeholder with a real
FastAPI dependency that validates authentication and returns the authenticated
user's info, or explicitly raise an HTTPException (401 Unauthorized) or a 501
Not Implemented if auth is not yet available. Implement using FastAPI's Depends
to accept an auth token or API key (or plug into your existing auth backend),
validate the credential, extract and return user_id and tenant_id on success,
and ensure unauthorized or unimplemented paths raise the appropriate
HTTPException with a clear message.
```

</details>

===

_🛠️ Refactor suggestion_

**Sanitize error responses and include correlation_id; log stack traces.**

Avoid leaking `str(e)` to clients; use `logger.exception` and return tenant-safe details with correlation_id.

```diff
-        logger.error(
-            "Business analysis execution failed",
-            correlation_id=correlation_id,
-            error=str(e),
-        )
-        raise HTTPException(
-            status_code=500,
-            detail=f"Business analysis failed: {str(e)}"
-        )
+        logger.exception(
+            "Business analysis execution failed",
+            correlation_id=correlation_id,
+        )
+        raise HTTPException(
+            status_code=500,
+            detail={"message": "Business analysis failed", "correlation_id": correlation_id},
+        )
```

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
    except Exception as e:
        logger.exception(
            "Business analysis execution failed",
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=500,
            detail={"message": "Business analysis failed", "correlation_id": correlation_id},
        )
```

</details>

<!-- suggestion_end -->

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 Ruff (0.13.1)</summary>

123-123: Do not catch blind exception: `Exception`

(BLE001)

---

124-128: Use `logging.exception` instead of `logging.error`

Replace with `exception`

(TRY400)

---

129-132: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

(B904)

---

131-131: Use explicit conversion flag

Replace with conversion flag

(RUF010)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In backend/app/api/routes/agents.py around lines 123 to 132, avoid returning the
raw exception string to clients and instead log the full stack trace while
returning a tenant-safe message that includes the correlation_id; replace the
current logger.error(...) with logger.exception(...) (or logger.error(...,
exc_info=True)) to capture stack traces and ensure the correlation_id is
included in the log fields, then raise HTTPException with a generic error detail
(e.g., "Business analysis failed") plus the correlation_id (for support lookup)
but do not include str(e) in the response.
```

</details>

===

_🛠️ Refactor suggestion_

**Apply the same sanitized error handling pattern here.**

```diff
-        logger.error(
-            "Architecture design execution failed",
-            correlation_id=correlation_id,
-            error=str(e),
-        )
-        raise HTTPException(
-            status_code=500,
-            detail=f"Architecture design failed: {str(e)}"
-        )
+        logger.exception("Architecture design execution failed", correlation_id=correlation_id)
+        raise HTTPException(status_code=500, detail={"message": "Architecture design failed", "correlation_id": correlation_id})
```

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
    except Exception as e:
        logger.exception("Architecture design execution failed", correlation_id=correlation_id)
        raise HTTPException(status_code=500, detail={"message": "Architecture design failed", "correlation_id": correlation_id})
```

</details>

<!-- suggestion_end -->

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 Ruff (0.13.1)</summary>

164-164: Do not catch blind exception: `Exception`

(BLE001)

---

165-169: Use `logging.exception` instead of `logging.error`

Replace with `exception`

(TRY400)

---

170-173: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

(B904)

---

172-172: Use explicit conversion flag

Replace with conversion flag

(RUF010)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In backend/app/api/routes/agents.py around lines 164 to 173, replace the current
handling that logs and returns the raw exception string with the project's
sanitized error pattern: log the full error (including stack/exception info and
correlation_id) but do not embed str(e) into the HTTP response. Update the
logger call to record the error with exc_info/stacktrace and correlation_id, and
change the HTTPException detail to a generic message like "Architecture design
failed" (no raw error text) while keeping status_code 500.
```

</details>

===

_🛠️ Refactor suggestion_

**Apply sanitized error handling for implementation planning.**

```diff
-        logger.error(
-            "Implementation planning execution failed",
-            correlation_id=correlation_id,
-            error=str(e),
-        )
-        raise HTTPException(
-            status_code=500,
-            detail=f"Implementation planning failed: {str(e)}"
-        )
+        logger.exception("Implementation planning execution failed", correlation_id=correlation_id)
+        raise HTTPException(status_code=500, detail={"message": "Implementation planning failed", "correlation_id": correlation_id})
```

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
    except Exception as e:
        logger.exception("Implementation planning execution failed", correlation_id=correlation_id)
        raise HTTPException(status_code=500, detail={"message": "Implementation planning failed", "correlation_id": correlation_id})
```

</details>

<!-- suggestion_end -->

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 Ruff (0.13.1)</summary>

206-206: Do not catch blind exception: `Exception`

(BLE001)

---

207-211: Use `logging.exception` instead of `logging.error`

Replace with `exception`

(TRY400)

---

212-215: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

(B904)

---

214-214: Use explicit conversion flag

Replace with conversion flag

(RUF010)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In backend/app/api/routes/agents.py around lines 206 to 215, replace the current
pattern that logs and returns the raw exception string with sanitized error
handling: log the full exception details server-side (use logger.exception or
logger.error with stack/trace and include correlation_id) but do NOT include
str(e) in the HTTPException detail returned to the client; instead return a
generic message like "Implementation planning failed" (and keep correlation_id
in logs so clients can report it). Ensure no sensitive data from the exception
is sent to the response.
```

</details>

===

_🛠️ Refactor suggestion_

**Apply sanitized error handling for engineering standards.**

```diff
-        logger.error(
-            "Engineering standards execution failed",
-            correlation_id=correlation_id,
-            error=str(e),
-        )
-        raise HTTPException(
-            status_code=500,
-            detail=f"Engineering standards failed: {str(e)}"
-        )
+        logger.exception("Engineering standards execution failed", correlation_id=correlation_id)
+        raise HTTPException(status_code=500, detail={"message": "Engineering standards failed", "correlation_id": correlation_id})
```

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
    except Exception as e:
        logger.exception("Engineering standards execution failed", correlation_id=correlation_id)
        raise HTTPException(status_code=500, detail={"message": "Engineering standards failed", "correlation_id": correlation_id})
```

</details>

<!-- suggestion_end -->

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 Ruff (0.13.1)</summary>

248-248: Do not catch blind exception: `Exception`

(BLE001)

---

249-253: Use `logging.exception` instead of `logging.error`

Replace with `exception`

(TRY400)

---

254-257: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling

(B904)

---

256-256: Use explicit conversion flag

Replace with conversion flag

(RUF010)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In backend/app/api/routes/agents.py around lines 248 to 257, the current handler
logs and returns the raw exception message which can leak sensitive/internal
details; instead, log the full exception including stack trace and
correlation_id (e.g., use logger.exception or include traceback) but raise an
HTTPException with a sanitized, non-sensitive detail message (for example
"Engineering standards failed" plus the correlation_id) so clients get a useful
reference without exposing internal error content.
```

</details>

===

_⚠️ Potential issue_

**Remove hardcoded tech stack fallback in SSE.**

Hardcoded values in backend are disallowed. Fail the step if stack cannot be parsed.

```diff
-            # Extract technology stack from architecture result for standards step
-            tech_stack = ["FastAPI", "PostgreSQL", "Docker"]  # Default fallback
-            try:
-                if arch_result.get("content"):
-                    # TODO 04: Parse technology stack from architecture content
-                    pass
-            except:
-                pass
+            # Extract technology stack from architecture result for standards step
+            tech_stack: list[str] = []
+            # TODO: parse stack from arch_result content deterministically
+            if not tech_stack:
+                raise ValueError("Unable to determine technology stack from architecture result")
```

> Committable suggestion skipped: line range outside the PR's diff.

<details>
<summary>🧰 Tools</summary>

<details>
<summary>🪛 Ruff (0.13.1)</summary>

359-359: Do not use bare `except`

(E722)

---

359-360: `try`-`except`-`pass` detected, consider logging the exception

(S110)

</details>

</details>

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In backend/app/api/routes/agents.py around lines 352 to 361, the code currently
uses a hardcoded tech_stack fallback which is disallowed; replace this by
parsing the technology stack from arch_result["content"] and fail the step when
parsing cannot produce a valid list. Specifically, remove the
["FastAPI","PostgreSQL","Docker"] default, attempt to extract/parse a tech stack
(e.g. JSON or newline/commaseparated tokens) from arch_result.get("content"),
validate that the result is a non-empty list of strings, and if parsing fails
raise an exception or return an SSE error to abort the step (avoid catching
exceptions with a bare except; catch specific exceptions, log the error context,
and propagate failure).
```

</details>

===

_🛠️ Refactor suggestion_

**Return 501 for unimplemented status endpoint.**

Backend guidelines: proper HTTP codes; avoid TODO placeholders in responses.

```diff
-    # TODO 04: Implement workflow status tracking with Redis/database
-    return {
-        "workflow_id": workflow_id,
-        "status": "not_implemented",
-        "message": "Status tracking not yet implemented",
-        "timestamp": datetime.now(timezone.utc).isoformat()
-    }
+    raise HTTPException(status_code=501, detail="Workflow status tracking not implemented")
```

> Committable suggestion skipped: line range outside the PR's diff.

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In backend/app/api/routes/agents.py around lines 423 to 429, replace the TODO
placeholder JSON response with a proper 501 Not Implemented HTTP response: raise
fastapi.HTTPException(status_code=501, detail={"workflow_id": workflow_id,
"message": "Status tracking not yet implemented", "timestamp":
datetime.now(timezone.utc).isoformat()}) or return a Response/JSONResponse with
status_code=501 and the same JSON body; ensure fastapi.HTTPException or
JSONResponse is imported if not already.
```

</details>

===

_🛠️ Refactor suggestion_

**Return 501 for unimplemented history endpoint.**

Same rationale as status endpoint.

```diff
-    # TODO 04: Implement execution history retrieval from database
-    return {
-        "project_id": project_id,
-        "executions": [],
-        "message": "Execution history not yet implemented",
-        "timestamp": datetime.now(timezone.utc).isoformat()
-    }
+    raise HTTPException(status_code=501, detail="Execution history not implemented")
```

<!-- suggestion_start -->

<details>
<summary>📝 Committable suggestion</summary>

> ‼️ **IMPORTANT**
> Carefully review the code before committing. Ensure that it accurately replaces the highlighted code, contains no missing lines, and has no issues with indentation. Thoroughly test & benchmark the code to ensure it meets the requirements.

```suggestion
    raise HTTPException(status_code=501, detail="Execution history not implemented")
```

</details>

<!-- suggestion_end -->

<details>
<summary>🤖 Prompt for AI Agents</summary>

```
In backend/app/api/routes/agents.py around lines 438 to 444, the unimplemented
execution history endpoint currently returns a 200 with a placeholder payload;
change it to return HTTP 501 Not Implemented instead. Replace the current return
with either raise HTTPException(status_code=501, detail={ "project_id":
project_id, "executions": [], "message": "Execution history not yet
implemented", "timestamp": datetime.now(timezone.utc).isoformat() }) or return
JSONResponse(content={...same payload...}, status_code=501); ensure the relevant
import (fastapi.HTTPException or fastapi.responses.JSONResponse) is present and
keep the payload structure and timestamp generation unchanged.
```

</details>
