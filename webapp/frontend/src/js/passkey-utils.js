/**
 * PassKey Utilities - Reusable functions for WebAuthn PassKey authentication
 * Used for secure confirmations throughout the application
 */

/**
 * Show a confirmation dialog with PassKey verification
 * @param {string} message - The confirmation message to display
 * @param {string} operationContext - Context for the operation being confirmed
 * @param {Object} options - Additional options
 * @returns {Promise<boolean>} - True if confirmed and authenticated, false otherwise
 */
export async function confirmWithPassKey(message, operationContext, options = {}) {
  return new Promise((resolve) => {
    // Create modal HTML
    const modalId = `passkey-confirm-${Date.now()}`;
    const modalHTML = `
      <div id="${modalId}" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50"
           x-data="passkeyConfirmDialog('${operationContext}')"
           x-show="open"
           x-transition:enter="ease-out duration-300"
           x-transition:enter-start="opacity-0"
           x-transition:enter-end="opacity-100"
           x-transition:leave="ease-in duration-200"
           x-transition:leave-start="opacity-100"
           x-transition:leave-end="opacity-0">

        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white"
             x-transition:enter="ease-out duration-300"
             x-transition:enter-start="opacity-0 transform scale-95"
             x-transition:enter-end="opacity-100 transform scale-100"
             x-transition:leave="ease-in duration-200"
             x-transition:leave-start="opacity-100 transform scale-100"
             x-transition:leave-end="opacity-0 transform scale-95">

          <!-- Header -->
          <div class="mt-3 text-center">
            <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100">
              <svg class="h-6 w-6 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.623 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
              </svg>
            </div>
            <h3 class="text-lg leading-6 font-medium text-gray-900 mt-2">Confirm with PassKey</h3>
            <div class="mt-2 px-7 py-3">
              <p class="text-sm text-gray-500">${message}</p>
              <div x-show="error" class="mt-3 p-2 bg-red-50 border border-red-200 rounded-md">
                <p class="text-sm text-red-800" x-text="error"></p>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="items-center px-4 py-3 flex justify-between">
            <button @click="cancel()"
                    :disabled="authenticating"
                    class="px-4 py-2 bg-gray-500 text-white text-base font-medium rounded-md shadow-sm hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-300 disabled:opacity-50">
              Cancel
            </button>

            <button @click="authenticate()"
                    :disabled="authenticating"
                    class="px-4 py-2 bg-primary-600 text-white text-base font-medium rounded-md shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 flex items-center">
              <svg x-show="authenticating" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span x-text="authenticating ? 'Authenticating...' : 'Confirm with PassKey'"></span>
            </button>
          </div>
        </div>
      </div>
    `;

    // Add modal to DOM
    const modalDiv = document.createElement('div');
    modalDiv.innerHTML = modalHTML;
    document.body.appendChild(modalDiv);

    // Alpine.js component for the modal
    window.passkeyConfirmDialog = (operationContext) => ({
      open: true,
      authenticating: false,
      error: null,

      async authenticate() {
        try {
          this.authenticating = true;
          this.error = null;

          const auth = Alpine.store('auth');

          // Check WebAuthn support
          if (!window.PublicKeyCredential) {
            throw new Error('WebAuthn is not supported in this browser');
          }

          // Get authentication challenge from server
          const challengeResponse = await fetch('/api/auth/passkeys/authentication-challenge', {
            method: 'POST',
            headers: {
              ...auth.getAuthHeaders(),
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ operation_context: operationContext }),
          });

          if (!challengeResponse.ok) {
            const error = await challengeResponse.json();
            throw new Error(error.detail || 'Failed to get authentication challenge');
          }

          const challengeData = await challengeResponse.json();

          // Convert base64url challenge to ArrayBuffer
          const challenge = Uint8Array.from(atob(challengeData.challenge.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));

          // Convert allowCredentials to proper format
          const allowCredentials = challengeData.allowCredentials.map(cred => ({
            ...cred,
            id: Uint8Array.from(atob(cred.id.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0))
          }));

          // Perform WebAuthn authentication
          const assertion = await navigator.credentials.get({
            publicKey: {
              challenge: challenge,
              allowCredentials: allowCredentials,
              rpId: challengeData.rpId,
              timeout: challengeData.timeout || 60000,
              userVerification: challengeData.userVerification || 'preferred'
            }
          });

          if (!assertion) {
            throw new Error('PassKey authentication was cancelled');
          }

          // Convert assertion response to format expected by server
          const authenticationData = {
            id: assertion.id,
            rawId: btoa(String.fromCharCode(...new Uint8Array(assertion.rawId))),
            response: {
              clientDataJSON: btoa(String.fromCharCode(...new Uint8Array(assertion.response.clientDataJSON))),
              authenticatorData: btoa(String.fromCharCode(...new Uint8Array(assertion.response.authenticatorData))),
              signature: btoa(String.fromCharCode(...new Uint8Array(assertion.response.signature))),
              userHandle: assertion.response.userHandle ? btoa(String.fromCharCode(...new Uint8Array(assertion.response.userHandle))) : null,
            },
            type: assertion.type,
          };

          // Send assertion to server for verification
          const verificationResponse = await fetch('/api/auth/passkeys/verify-authentication', {
            method: 'POST',
            headers: {
              ...auth.getAuthHeaders(),
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              ...authenticationData,
              operation_context: operationContext
            }),
          });

          if (!verificationResponse.ok) {
            const error = await verificationResponse.json();
            throw new Error(error.detail || 'Failed to verify PassKey authentication');
          }

          const result = await verificationResponse.json();
          console.log('PassKey authentication successful:', result);

          // Close modal and resolve with success
          this.close(true);

        } catch (error) {
          console.error('Failed to authenticate with PassKey:', error);
          this.error = error.message;
        } finally {
          this.authenticating = false;
        }
      },

      cancel() {
        this.close(false);
      },

      close(result) {
        this.open = false;

        // Remove modal from DOM after transition
        setTimeout(() => {
          const modalElement = document.getElementById('${modalId}');
          if (modalElement) {
            modalElement.parentElement.remove();
          }
          resolve(result);
        }, 200);
      }
    });
  });
}

/**
 * Simple PassKey authentication without UI dialog
 * @param {string} operationContext - Context for the operation
 * @returns {Promise<Object>} - Authentication result object
 */
export async function authenticateWithPassKey(operationContext = null) {
  const auth = Alpine.store('auth');

  // Check WebAuthn support
  if (!window.PublicKeyCredential) {
    throw new Error('WebAuthn is not supported in this browser');
  }

  // Get authentication challenge from server
  const challengeResponse = await fetch('/api/auth/passkeys/authentication-challenge', {
    method: 'POST',
    headers: {
      ...auth.getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ operation_context: operationContext }),
  });

  if (!challengeResponse.ok) {
    const error = await challengeResponse.json();
    throw new Error(error.detail || 'Failed to get authentication challenge');
  }

  const challengeData = await challengeResponse.json();

  // Convert base64url challenge to ArrayBuffer
  const challenge = Uint8Array.from(atob(challengeData.challenge.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));

  // Convert allowCredentials to proper format
  const allowCredentials = challengeData.allowCredentials.map(cred => ({
    ...cred,
    id: Uint8Array.from(atob(cred.id.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0))
  }));

  // Perform WebAuthn authentication
  const assertion = await navigator.credentials.get({
    publicKey: {
      challenge: challenge,
      allowCredentials: allowCredentials,
      rpId: challengeData.rpId,
      timeout: challengeData.timeout || 60000,
      userVerification: challengeData.userVerification || 'preferred'
    }
  });

  if (!assertion) {
    throw new Error('PassKey authentication was cancelled');
  }

  // Convert assertion response to format expected by server
  const authenticationData = {
    id: assertion.id,
    rawId: btoa(String.fromCharCode(...new Uint8Array(assertion.rawId))),
    response: {
      clientDataJSON: btoa(String.fromCharCode(...new Uint8Array(assertion.response.clientDataJSON))),
      authenticatorData: btoa(String.fromCharCode(...new Uint8Array(assertion.response.authenticatorData))),
      signature: btoa(String.fromCharCode(...new Uint8Array(assertion.response.signature))),
      userHandle: assertion.response.userHandle ? btoa(String.fromCharCode(...new Uint8Array(assertion.response.userHandle))) : null,
    },
    type: assertion.type,
  };

  // Send assertion to server for verification
  const verificationResponse = await fetch('/api/auth/passkeys/verify-authentication', {
    method: 'POST',
    headers: {
      ...auth.getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...authenticationData,
      operation_context: operationContext
    }),
  });

  if (!verificationResponse.ok) {
    const error = await verificationResponse.json();
    throw new Error(error.detail || 'Failed to verify PassKey authentication');
  }

  return await verificationResponse.json();
}

/**
 * Check if user has any PassKeys registered
 * @returns {Promise<boolean>} - True if user has PassKeys, false otherwise
 */
export async function hasPassKeys() {
  try {
    const auth = Alpine.store('auth');

    const response = await fetch('/api/auth/passkeys', {
      headers: auth.getAuthHeaders(),
    });

    if (response.ok) {
      const data = await response.json();
      return data.passkeys && data.passkeys.length > 0;
    }

    return false;
  } catch (error) {
    console.error('Error checking for PassKeys:', error);
    return false;
  }
}