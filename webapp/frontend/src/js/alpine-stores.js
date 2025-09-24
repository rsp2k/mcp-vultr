/**
 * Alpine.js Stores and Utilities
 * Complete store architecture for Service Collections Management
 */

// Import PassKey utilities
import { confirmWithPassKey, authenticateWithPassKey, hasPassKeys } from './passkey-utils.js';

// Utility function to get authentication headers
function getAuthHeaders() {
  const token = localStorage.getItem('auth_token');
  return {
    'Content-Type': 'application/json',
    'Authorization': token ? `Bearer ${token}` : ''
  };
}

// Notification system
window.notification = function() {
  return {
    visible: false,
    type: 'info',
    message: '',

    show(type, message, duration = 5000) {
      this.type = type;
      this.message = message;
      this.visible = true;

      setTimeout(() => {
        this.hide();
      }, duration);
    },

    hide() {
      this.visible = false;
    }
  };
};

// Modal utility
window.modal = function() {
  return {
    isOpen: false,

    open() {
      this.isOpen = true;
      document.body.style.overflow = 'hidden';
    },

    close() {
      this.isOpen = false;
      document.body.style.overflow = 'auto';
    }
  };
};

// Dropdown utility
window.dropdown = function() {
  return {
    isOpen: false,

    toggle() {
      this.isOpen = !this.isOpen;
    },

    close() {
      this.isOpen = false;
    }
  };
};

// PassKey confirmation dialog component
window.passkeyConfirmDialog = function(operationContext) {
  return {
    open: true,
    loading: false,
    error: null,

    async confirm() {
      this.loading = true;
      this.error = null;

      try {
        const result = await authenticateWithPassKey(operationContext);

        if (result) {
          // Close dialog and resolve with success
          this.close(true);
        } else {
          this.error = 'Authentication failed. Please try again.';
        }
      } catch (error) {
        console.error('PassKey authentication error:', error);
        this.error = error.message || 'Authentication failed. Please try again.';
      }

      this.loading = false;
    },

    close(confirmed = false) {
      this.open = false;

      // Remove modal from DOM after animation
      setTimeout(() => {
        const modal = document.getElementById(`passkey-confirm-${Date.now()}`);
        if (modal && modal.parentNode) {
          modal.parentNode.removeChild(modal);
        }
      }, 300);

      // Resolve the promise from confirmWithPassKey
      if (window.passkeyConfirmResolve) {
        window.passkeyConfirmResolve(confirmed);
        window.passkeyConfirmResolve = null;
      }
    }
  };
};

// Wait for Alpine.js to be available then register stores immediately
function registerStores() {
  if (typeof Alpine !== 'undefined') {
    console.log('🎯 Registering Alpine.js stores...');

    // Authentication Store
    Alpine.store('auth', {
    user: null,
    token: localStorage.getItem('auth_token'),
    authConfig: null,
    loading: false,

    async init() {
      console.log('🔐 Initializing auth store...');

      // Get auth configuration
      try {
        const response = await fetch('/api/auth/config');
        if (response.ok) {
          this.authConfig = await response.json();
        } else {
          console.warn('Failed to load auth config');
          this.authConfig = {};
        }
      } catch (error) {
        console.error('Error loading auth config:', error);
        this.authConfig = {};
      }

      // Check if we have a token and validate it
      if (this.token) {
        await this.checkAuth();
      }
    },

    async checkAuth() {
      if (!this.token) {
        return false;
      }

      try {
        const response = await fetch('/api/auth/me', {
          headers: getAuthHeaders()
        });

        if (response.ok) {
          this.user = await response.json();
          return true;
        } else {
          // Token is invalid, clear it
          this.logout();
          return false;
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        this.logout();
        return false;
      }
    },

    async login(email, password) {
      this.loading = true;

      try {
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ email, password })
        });

        const result = await response.json();

        if (response.ok) {
          this.token = result.access_token;
          this.user = result.user;
          localStorage.setItem('auth_token', this.token);

          return { success: true };
        } else {
          return { success: false, error: result.detail || 'Login failed' };
        }
      } catch (error) {
        console.error('Login error:', error);
        return { success: false, error: 'Network error occurred' };
      } finally {
        this.loading = false;
      }
    },

    async loginWithGitHub() {
      try {
        // Redirect to GitHub OAuth
        window.location.href = '/api/auth/github/login';
        return { success: true };
      } catch (error) {
        console.error('GitHub OAuth error:', error);
        return { success: false, error: 'Failed to initiate GitHub login' };
      }
    },

    logout() {
      this.user = null;
      this.token = null;
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
  });

  // Collections Store
  Alpine.store('collections', {
    items: [],
    loading: false,
    error: null,
    total: 0,

    async fetchCollections(filters = {}) {
      this.loading = true;
      this.error = null;

      try {
        // Build query parameters
        const params = new URLSearchParams();
        if (filters.environment) params.append('environment', filters.environment);
        if (filters.status) params.append('status', filters.status);
        if (filters.limit) params.append('limit', filters.limit.toString());
        if (filters.offset) params.append('offset', filters.offset.toString());

        const response = await fetch(`/api/collections?${params.toString()}`, {
          headers: getAuthHeaders()
        });

        if (response.ok) {
          const data = await response.json();
          this.items = data.collections || [];
          this.total = data.total || 0;
        } else {
          const errorData = await response.json();
          this.error = errorData.detail || 'Failed to load collections';
          this.items = [];
        }
      } catch (error) {
        console.error('Error fetching collections:', error);
        this.error = 'Network error occurred';
        this.items = [];
      } finally {
        this.loading = false;
      }
    },

    async createCollection(data) {
      try {
        // First check if user has PassKeys for confirmation
        const userHasPassKeys = await hasPassKeys();

        if (userHasPassKeys) {
          // Require PassKey confirmation for production environments
          if (data.environment === 'production') {
            const confirmed = await confirmWithPassKey(
              `Create production Service Collection "${data.name}"?`,
              'collection_creation_production'
            );

            if (!confirmed) {
              return { success: false, error: 'Creation cancelled' };
            }
          }
        }

        const response = await fetch('/api/collections', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify(data)
        });

        if (response.ok) {
          const newCollection = await response.json();
          this.items.unshift(newCollection);
          this.total += 1;

          // Show success notification
          if (window.Alpine && Alpine.store('notification')) {
            Alpine.store('notification').show('success', `Collection "${data.name}" created successfully`);
          }

          return { success: true, data: newCollection };
        } else {
          const errorData = await response.json();
          const error = errorData.detail || 'Failed to create collection';

          // Show error notification
          if (window.Alpine && Alpine.store('notification')) {
            Alpine.store('notification').show('error', error);
          }

          return { success: false, error };
        }
      } catch (error) {
        console.error('Error creating collection:', error);
        const errorMsg = 'Network error occurred';

        if (window.Alpine && Alpine.store('notification')) {
          Alpine.store('notification').show('error', errorMsg);
        }

        return { success: false, error: errorMsg };
      }
    },

    async updateCollection(id, data) {
      try {
        // Require PassKey confirmation for production collections
        const collection = this.items.find(item => item.id === id);
        if (collection && collection.environment === 'production') {
          const userHasPassKeys = await hasPassKeys();
          if (userHasPassKeys) {
            const confirmed = await confirmWithPassKey(
              `Update production Service Collection "${collection.name}"?`,
              'collection_update_production'
            );

            if (!confirmed) {
              return { success: false, error: 'Update cancelled' };
            }
          }
        }

        const response = await fetch(`/api/collections/${id}`, {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify(data)
        });

        if (response.ok) {
          const updatedCollection = await response.json();
          const index = this.items.findIndex(item => item.id === id);
          if (index !== -1) {
            this.items[index] = updatedCollection;
          }

          if (window.Alpine && Alpine.store('notification')) {
            Alpine.store('notification').show('success', 'Collection updated successfully');
          }

          return { success: true, data: updatedCollection };
        } else {
          const errorData = await response.json();
          const error = errorData.detail || 'Failed to update collection';

          if (window.Alpine && Alpine.store('notification')) {
            Alpine.store('notification').show('error', error);
          }

          return { success: false, error };
        }
      } catch (error) {
        console.error('Error updating collection:', error);
        const errorMsg = 'Network error occurred';

        if (window.Alpine && Alpine.store('notification')) {
          Alpine.store('notification').show('error', errorMsg);
        }

        return { success: false, error: errorMsg };
      }
    },

    async deleteCollection(id) {
      try {
        const collection = this.items.find(item => item.id === id);
        if (!collection) {
          return { success: false, error: 'Collection not found' };
        }

        // Always require PassKey confirmation for deletion
        const userHasPassKeys = await hasPassKeys();
        if (userHasPassKeys) {
          const confirmed = await confirmWithPassKey(
            `Permanently delete Service Collection "${collection.name}"?\n\nThis action cannot be undone.`,
            'collection_deletion'
          );

          if (!confirmed) {
            return { success: false, error: 'Deletion cancelled' };
          }
        } else {
          // Fallback to regular confirm dialog if no PassKeys
          const confirmed = confirm(`Permanently delete Service Collection "${collection.name}"?\n\nThis action cannot be undone.`);
          if (!confirmed) {
            return { success: false, error: 'Deletion cancelled' };
          }
        }

        const response = await fetch(`/api/collections/${id}`, {
          method: 'DELETE',
          headers: getAuthHeaders()
        });

        if (response.ok) {
          this.items = this.items.filter(item => item.id !== id);
          this.total -= 1;

          if (window.Alpine && Alpine.store('notification')) {
            Alpine.store('notification').show('success', `Collection "${collection.name}" deleted successfully`);
          }

          return { success: true };
        } else {
          const errorData = await response.json();
          const error = errorData.detail || 'Failed to delete collection';

          if (window.Alpine && Alpine.store('notification')) {
            Alpine.store('notification').show('error', error);
          }

          return { success: false, error };
        }
      } catch (error) {
        console.error('Error deleting collection:', error);
        const errorMsg = 'Network error occurred';

        if (window.Alpine && Alpine.store('notification')) {
          Alpine.store('notification').show('error', errorMsg);
        }

        return { success: false, error: errorMsg };
      }
    }
  });

  // Dashboard Store
  Alpine.store('dashboard', {
    overview: null,
    loading: false,
    error: null,

    async fetchOverview() {
      this.loading = true;
      this.error = null;

      try {
        const response = await fetch('/api/dashboard/overview', {
          headers: getAuthHeaders()
        });

        if (response.ok) {
          this.overview = await response.json();
        } else {
          // Create mock data if endpoint doesn't exist yet
          this.overview = {
            summary: {
              total_collections: 0,
              active_operations: 0,
              monthly_cost: 0,
              this_month_activity: 0
            },
            recent_collections: [],
            recent_activities: []
          };
        }
      } catch (error) {
        console.error('Error fetching dashboard overview:', error);
        this.error = 'Failed to load dashboard overview';

        // Provide fallback data
        this.overview = {
          summary: {
            total_collections: 0,
            active_operations: 0,
            monthly_cost: 0,
            this_month_activity: 0
          },
          recent_collections: [],
          recent_activities: []
        };
      } finally {
        this.loading = false;
      }
    }
  });

  // Global notification store
  Alpine.store('notification', {
    visible: false,
    type: 'info',
    message: '',

    show(type, message, duration = 5000) {
      this.type = type;
      this.message = message;
      this.visible = true;

      setTimeout(() => {
        this.hide();
      }, duration);
    },

    hide() {
      this.visible = false;
    }
  });

  console.log('✅ Alpine.js stores registered successfully');
  } else {
    console.warn('⚠️ Alpine.js not yet available, stores not registered');
  }
}

// Check if Alpine is already available, otherwise wait for it
if (typeof Alpine !== 'undefined') {
  registerStores();
} else {
  // Alpine.js isn't loaded yet, wait for it
  document.addEventListener('DOMContentLoaded', () => {
    // Check periodically until Alpine is available
    const checkAlpine = setInterval(() => {
      if (typeof Alpine !== 'undefined') {
        clearInterval(checkAlpine);
        registerStores();
      }
    }, 10);
  });
}

console.log('🎯 Alpine.js store module loaded');