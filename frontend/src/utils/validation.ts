/**
 * Validation utilities for security and data integrity
 */

/**
 * Validates that a redirect path is safe (relative path only, no protocol/host)
 * @param path - The path to validate
 * @returns true if the path is safe, false otherwise
 */
export function isValidRedirectPath(path: string): boolean {
  if (!path || typeof path !== 'string') {
    return false;
  }

  // Must start with a single leading slash
  if (!path.startsWith('/')) {
    return false;
  }

  // Must not start with double slash (protocol-relative URL)
  if (path.startsWith('//')) {
    return false;
  }

  // Must not contain protocol or host portion
  // Check for common protocol patterns
  const protocolPattern = /^[a-zA-Z][a-zA-Z0-9+.-]*:/;
  if (protocolPattern.test(path)) {
    return false;
  }

  // Check for encoded protocol attempts
  const encodedProtocolPattern = /%[0-9a-fA-F]{2}.*:/;
  if (encodedProtocolPattern.test(path)) {
    return false;
  }

  return true;
}

/**
 * Type guard to check if location state has a valid "from" property
 * @param state - The location state to check
 * @returns Type predicate indicating if state has valid "from" property
 */
export function hasValidFromProperty(
  state: unknown
): state is { from: { pathname: string } } {
  if (!state || typeof state !== 'object') {
    return false;
  }

  const stateObj = state as Record<string, unknown>;

  if (!stateObj.from || typeof stateObj.from !== 'object') {
    return false;
  }

  const fromObj = stateObj.from as Record<string, unknown>;

  if (typeof fromObj.pathname !== 'string') {
    return false;
  }

  return isValidRedirectPath(fromObj.pathname);
}
