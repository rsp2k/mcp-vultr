import { defineMiddleware } from 'astro:middleware';
import { validateAuthToken } from './lib/auth.js';

// Types for user and authentication
interface User {
  id: string;
  email: string;
  full_name: string;
  is_admin: boolean;
  avatar_url?: string;
}

interface AuthContext {
  user: User | null;
  isAuthenticated: boolean;
}

// Pages that don't require authentication
const PUBLIC_ROUTES = ['/login', '/'];

// API routes that handle their own auth
const API_ROUTES_PATTERN = /^\/api\//;

/**
 * Get current project from cookie
 */
function getCurrentProject(request: Request): string | null {
  const cookies = request.headers.get('cookie');
  if (!cookies) return null;

  const match = cookies.match(/currentProject=([^;]+)/);
  if (!match) return null;

  try {
    const projectData = JSON.parse(decodeURIComponent(match[1]));
    return projectData.id || null;
  } catch {
    return null;
  }
}

export const onRequest = defineMiddleware(async (context, next) => {
  const { request, url, cookies, locals, redirect } = context;

  // Skip middleware for API routes (they handle their own auth)
  if (API_ROUTES_PATTERN.test(url.pathname)) {
    return next();
  }

  // Get auth token from cookie
  const authToken = cookies.get('auth_token')?.value;

  // Initialize auth context
  const authContext: AuthContext = {
    user: null,
    isAuthenticated: false
  };

  // Validate token if present
  if (authToken) {
    const user = await validateAuthToken(authToken);
    if (user) {
      authContext.user = user;
      authContext.isAuthenticated = true;

      // Also get current project for context
      const currentProjectId = getCurrentProject(request);
      locals.currentProjectId = currentProjectId;
    } else {
      // Invalid token - clear it
      cookies.delete('auth_token');
    }
  }

  // Add auth context to locals for use in pages
  locals.auth = authContext;

  // Check if route requires authentication
  const requiresAuth = !PUBLIC_ROUTES.includes(url.pathname);

  if (requiresAuth && !authContext.isAuthenticated) {
    // Special handling for dashboard with token parameter - allow it through for token processing
    if (url.pathname === '/dashboard' && url.searchParams.get('token')) {
      console.log('🔗 Middleware: Allowing dashboard with token through for processing');
      return next();
    }

    // Redirect to login with return URL
    const returnUrl = encodeURIComponent(url.pathname + url.search);
    return redirect(`/login?return=${returnUrl}`);
  }

  // If authenticated and trying to access login page, redirect to dashboard
  // BUT allow OAuth token processing (when return URL contains token)
  if (authContext.isAuthenticated && url.pathname === '/login') {
    const returnUrl = new URL(request.url).searchParams.get('return');

    // Check if this is an OAuth callback with a token
    const isOAuthCallback = returnUrl && returnUrl.includes('token=');

    if (!isOAuthCallback) {
      // Only redirect if this is not an OAuth callback
      return redirect(returnUrl ? decodeURIComponent(returnUrl) : '/dashboard');
    }
    // If it is OAuth callback, let the login page handle the token processing
  }

  return next();
});

// Extend Astro's locals type
declare global {
  namespace App {
    interface Locals {
      auth: AuthContext;
      currentProjectId: string | null;
    }
  }
}