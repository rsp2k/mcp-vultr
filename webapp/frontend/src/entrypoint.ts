import type { Alpine } from 'alpinejs'

export default (Alpine: Alpine) => {

  // Global Alpine.js configuration and stores

  // Authentication store
  Alpine.store('auth', {
    user: null,
    token: localStorage.getItem('auth_token'),
    isAuthenticated: false,
    authConfig: null,
    _initialized: false,
    _initializing: false,

    async init() {
      // Prevent multiple simultaneous initializations
      if (this._initialized || this._initializing) {
        console.log('🔐 Auth store already initialized/initializing, skipping...');
        return;
      }

      this._initializing = true;
      console.log('🔐 Auth store init called', {
        url: window.location.href,
        search: window.location.search,
        existing_token: this.token ? this.token.substring(0, 20) + '...' : null
      });

      try {
        // Check for token in URL parameters (OAuth callback)
        const urlParams = new URLSearchParams(window.location.search);
        const urlToken = urlParams.get('token');

        console.log('🔑 Token extraction:', {
          urlToken: urlToken ? urlToken.substring(0, 20) + '...' : null,
          urlParams: urlParams.toString(),
          hasToken: !!urlToken
        });

        if (urlToken) {
          console.log('✅ Found token in URL, storing...');
          // Store token from URL and remove from URL
          this.token = urlToken;
          localStorage.setItem('auth_token', urlToken);

          // Clean up URL by removing token parameter
          const newUrl = new URL(window.location.href);
          newUrl.searchParams.delete('token');
          window.history.replaceState({}, '', newUrl.toString());

          console.log('🔄 Calling checkAuth after token storage');
          await this.checkAuth();
        } else if (this.token) {
          console.log('🔄 Calling checkAuth with existing token');
          await this.checkAuth();
        } else {
          console.log('❌ No token found in URL or store');
        }

        await this.loadAuthConfig();
        this._initialized = true;
      } finally {
        this._initializing = false;
      }
    },
    
    async loadAuthConfig() {
      try {
        const response = await fetch('/api/auth/config');
        if (response.ok) {
          this.authConfig = await response.json();
        }
      } catch (error) {
        console.warn('Failed to load auth config:', error);
      }
    },
    
    async login(email: string, password: string) {
      try {
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, password }),
        });
        
        if (response.ok) {
          const data = await response.json();
          this.token = data.access_token;
          this.user = data.user;
          this.isAuthenticated = true;
          localStorage.setItem('auth_token', this.token);
          return { success: true };
        } else {
          const error = await response.json();
          return { success: false, error: error.message };
        }
      } catch (error) {
        return { success: false, error: 'Network error' };
      }
    },
    
    async loginWithGitHub() {
      try {
        const response = await fetch('/api/auth/github/authorize', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({})
        });
        
        if (response.ok) {
          const data = await response.json();
          // Redirect to GitHub authorization URL
          window.location.href = data.authorization_url;
          return { success: true };
        } else {
          const error = await response.json();
          return { success: false, error: error.message };
        }
      } catch (error) {
        return { success: false, error: 'Network error' };
      }
    },
    
    async logout() {
      try {
        if (this.token) {
          await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${this.token}`,
            },
          });
        }
      } catch (error) {
        console.warn('Logout request failed:', error);
      } finally {
        this.token = null;
        this.user = null;
        this.isAuthenticated = false;
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
    },
    
    async checkAuth() {
      console.log('🔍 checkAuth called', {
        hasToken: !!this.token,
        tokenPrefix: this.token ? this.token.substring(0, 20) + '...' : null
      });

      if (!this.token) {
        console.log('❌ No token available for auth check');
        return false;
      }

      try {
        console.log('📡 Making /api/auth/me request...');
        const response = await fetch('/api/auth/me', {
          headers: {
            'Authorization': `Bearer ${this.token}`,
          },
        });

        console.log('📡 Auth response:', {
          status: response.status,
          ok: response.ok
        });

        if (response.ok) {
          this.user = await response.json();
          this.isAuthenticated = true;
          console.log('✅ Authentication successful', { user: this.user });
          return true;
        } else {
          console.log('❌ Authentication failed, logging out');
          this.logout();
          return false;
        }
      } catch (error) {
        console.log('💥 Auth check error:', error);
        this.logout();
        return false;
      }
    },
    
    getAuthHeaders() {
      return this.token ? { 'Authorization': `Bearer ${this.token}` } : {};
    }
  });

  // Projects Store
  Alpine.store('projects', {
    items: [],
    loading: false,
    error: null,
    currentProject: null,
    total: 0,
    initialized: false,

    init() {
      if (this.initialized) return;

      // Load current project from localStorage
      const stored = localStorage.getItem('currentProject');
      if (stored) {
        try {
          this.currentProject = JSON.parse(stored);
        } catch (e) {
          localStorage.removeItem('currentProject');
        }
      }

      this.initialized = true;
    },

    async fetchProjects(filters = {}) {
      this.loading = true;
      this.error = null;

      try {
        // Build query parameters - ensure we use the correct endpoint with trailing slash
        const params = new URLSearchParams();
        if (filters.status) params.append('status_filter', filters.status);
        if (filters.search) params.append('search', filters.search);
        if (filters.limit) params.append('limit', filters.limit.toString());
        if (filters.offset) params.append('offset', filters.offset.toString());

        const queryString = params.toString();
        const url = queryString ? `/api/projects/?${queryString}` : '/api/projects/';

        const auth = Alpine.store('auth');
        const response = await fetch(url, {
          headers: {
            'Content-Type': 'application/json',
            ...auth.getAuthHeaders()
          }
        });

        if (response.ok) {
          this.items = await response.json();
          this.total = this.items.length;
          this.error = null;

          // Auto-select first project if none is currently selected
          if (this.items.length > 0 && !this.currentProject) {
            console.log('🎯 Auto-selecting first project:', this.items[0].name);
            this.setCurrentProject(this.items[0]);
          }
        } else {
          const errorData = await response.json();
          this.error = errorData.detail || 'Failed to load projects';
          this.items = [];
          console.error('Projects fetch error:', errorData);
        }
      } catch (error) {
        console.error('Error fetching projects:', error);
        this.error = 'Network error occurred while loading projects';
        this.items = [];
      } finally {
        this.loading = false;
      }
    },

    async createProject(data) {
      try {
        const auth = Alpine.store('auth');
        const response = await fetch('/api/projects/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...auth.getAuthHeaders()
          },
          body: JSON.stringify(data)
        });

        if (response.ok) {
          const newProject = await response.json();
          this.items.unshift(newProject);
          this.total += 1;

          // Auto-select the newly created project if no project is currently selected
          if (!this.currentProject) {
            console.log('🎯 Auto-selecting newly created project:', newProject.name);
            this.setCurrentProject(newProject);
          }

          return { success: true, data: newProject };
        } else {
          const errorData = await response.json();
          const error = errorData.detail || 'Failed to create project';
          return { success: false, error };
        }
      } catch (error) {
        console.error('Error creating project:', error);
        return { success: false, error: 'Network error occurred' };
      }
    },

    async updateProject(id, data) {
      try {
        const auth = Alpine.store('auth');
        const response = await fetch(`/api/projects/${id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            ...auth.getAuthHeaders()
          },
          body: JSON.stringify(data)
        });

        if (response.ok) {
          const updatedProject = await response.json();
          const index = this.items.findIndex(item => item.id === id);
          if (index !== -1) {
            this.items[index] = updatedProject;
          }
          return { success: true, data: updatedProject };
        } else {
          const errorData = await response.json();
          const error = errorData.detail || 'Failed to update project';
          return { success: false, error };
        }
      } catch (error) {
        console.error('Error updating project:', error);
        return { success: false, error: 'Network error occurred' };
      }
    },

    async deleteProject(id) {
      try {
        const project = this.items.find(item => item.id === id);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        const auth = Alpine.store('auth');
        const response = await fetch(`/api/projects/${id}`, {
          method: 'DELETE',
          headers: auth.getAuthHeaders()
        });

        if (response.ok) {
          this.items = this.items.filter(item => item.id !== id);
          this.total -= 1;
          return { success: true };
        } else {
          const errorData = await response.json();
          const error = errorData.detail || 'Failed to delete project';
          return { success: false, error };
        }
      } catch (error) {
        console.error('Error deleting project:', error);
        return { success: false, error: 'Network error occurred' };
      }
    },

    setCurrentProject(project) {
      this.currentProject = project;
      localStorage.setItem('currentProject', JSON.stringify(project));

      // Dispatch event to notify other components
      window.dispatchEvent(new CustomEvent('project-changed', {
        detail: { project: project }
      }));
    },

    getCurrentProject() {
      if (!this.currentProject) {
        const stored = localStorage.getItem('currentProject');
        if (stored) {
          this.currentProject = JSON.parse(stored);
        }
      }
      return this.currentProject;
    },

    clearCurrentProject() {
      this.currentProject = null;
      localStorage.removeItem('currentProject');
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

  // Collections store for Service Collection management
  Alpine.store('collections', {
    items: [],
    loading: false,
    error: null,
    currentCollection: null,
    
    async fetchCollections(filters = {}) {
      this.loading = true;
      this.error = null;
      
      try {
        const auth = Alpine.store('auth');
        const params = new URLSearchParams(filters);
        const response = await fetch(`/api/collections?${params}`, {
          headers: auth.getAuthHeaders(),
        });
        
        if (response.ok) {
          const data = await response.json();
          this.items = data.collections;
        } else {
          this.error = 'Failed to fetch collections';
        }
      } catch (error) {
        this.error = 'Network error';
      } finally {
        this.loading = false;
      }
    },
    
    async createCollection(collectionData) {
      try {
        const auth = Alpine.store('auth');
        const response = await fetch('/api/collections', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...auth.getAuthHeaders(),
          },
          body: JSON.stringify(collectionData),
        });
        
        if (response.ok) {
          const newCollection = await response.json();
          this.items.unshift(newCollection);
          return { success: true, collection: newCollection };
        } else {
          const error = await response.json();
          return { success: false, error: error.message };
        }
      } catch (error) {
        return { success: false, error: 'Network error' };
      }
    },
    
    async deleteCollection(collectionId) {
      try {
        const auth = Alpine.store('auth');
        const response = await fetch(`/api/collections/${collectionId}`, {
          method: 'DELETE',
          headers: auth.getAuthHeaders(),
        });
        
        if (response.ok) {
          this.items = this.items.filter(item => item.id !== collectionId);
          return { success: true };
        } else {
          const error = await response.json();
          return { success: false, error: error.message };
        }
      } catch (error) {
        return { success: false, error: 'Network error' };
      }
    }
  });
  
  // Dashboard store for overview data
  Alpine.store('dashboard', {
    overview: null,
    loading: false,
    
    async fetchOverview() {
      this.loading = true;
      
      try {
        const auth = Alpine.store('auth');
        const response = await fetch('/api/dashboard/overview', {
          headers: auth.getAuthHeaders(),
        });
        
        if (response.ok) {
          this.overview = await response.json();
        }
      } catch (error) {
        console.error('Failed to fetch dashboard overview:', error);
      } finally {
        this.loading = false;
      }
    }
  });
  
  // Global Alpine data and methods
  Alpine.data('modal', () => ({
    isOpen: false,
    
    open() {
      this.isOpen = true;
      document.body.style.overflow = 'hidden';
    },
    
    close() {
      this.isOpen = false;
      document.body.style.overflow = '';
    },
    
    toggle() {
      this.isOpen ? this.close() : this.open();
    }
  }));
  
  Alpine.data('dropdown', () => ({
    isOpen: false,
    
    toggle() {
      this.isOpen = !this.isOpen;
    },
    
    close() {
      this.isOpen = false;
    }
  }));
  
  Alpine.data('notification', () => ({
    visible: false,
    message: '',
    type: 'info', // success, error, warning, info
    
    show(message: string, type = 'info') {
      this.message = message;
      this.type = type;
      this.visible = true;
      
      setTimeout(() => {
        this.hide();
      }, 5000);
    },
    
    hide() {
      this.visible = false;
    }
  }));
}