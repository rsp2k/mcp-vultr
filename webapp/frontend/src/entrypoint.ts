import type { Alpine } from 'alpinejs'

export default (Alpine: Alpine) => {

  // Global Alpine.js configuration and stores

  // Authentication store
  Alpine.store('auth', {
    user: null,
    token: localStorage.getItem('auth_token'),
    isAuthenticated: false,
    authConfig: null,
    
    async init() {
      console.log('🔐 Auth store init called', {
        url: window.location.href,
        search: window.location.search,
        existing_token: this.token
      });

      // Check for token in URL parameters (OAuth callback)
      const urlParams = new URLSearchParams(window.location.search);
      const urlToken = urlParams.get('token');

      console.log('🔑 Token extraction:', {
        urlToken,
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