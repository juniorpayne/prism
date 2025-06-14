/**
 * Tests for Router functionality
 * Test client-side routing, protected routes, and JWT handling
 */

describe('Router', () => {
    let router;
    
    beforeEach(() => {
        // Clear localStorage
        localStorage.clear();
        
        // Reset URL
        window.history.pushState({}, '', '/');
        
        // Create a new router instance
        router = new Router();
    });
    
    afterEach(() => {
        // Clean up
        localStorage.clear();
        window.history.pushState({}, '', '/');
    });
    
    describe('Navigation', () => {
        test('navigate() should change URL and handle route', (done) => {
            router.afterRoute((route, path) => {
                expect(path).toBe('/dashboard');
                expect(route.component).toBe('dashboard');
                expect(window.location.pathname).toBe('/dashboard');
                done();
            });
            
            router.navigate('/dashboard');
        });
        
        test('navigate() should not navigate to same path', () => {
            let callCount = 0;
            router.afterRoute(() => callCount++);
            
            router.navigate('/dashboard');
            router.navigate('/dashboard'); // Should not trigger
            
            expect(callCount).toBe(1);
        });
        
        test('browser back button should work', (done) => {
            router.navigate('/dashboard');
            router.navigate('/hosts');
            
            router.afterRoute((route, path) => {
                if (path === '/dashboard') {
                    expect(route.component).toBe('dashboard');
                    done();
                }
            });
            
            window.history.back();
        });
    });
    
    describe('Protected Routes', () => {
        test('protected route should redirect to login when not authenticated', (done) => {
            router.afterRoute((route, path) => {
                if (path === '/login') {
                    expect(route.protected).toBe(false);
                    expect(localStorage.getItem('redirectAfterLogin')).toBe('/dashboard');
                    done();
                }
            });
            
            router.navigate('/dashboard');
        });
        
        test('protected route should allow access with valid token', (done) => {
            // Create a valid JWT token (expires in 1 hour)
            const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
            const payload = btoa(JSON.stringify({ 
                exp: Math.floor(Date.now() / 1000) + 3600,
                sub: 'user123'
            }));
            const signature = 'fake-signature';
            const token = `${header}.${payload}.${signature}`;
            
            localStorage.setItem('accessToken', token);
            
            router.afterRoute((route, path) => {
                expect(path).toBe('/dashboard');
                expect(route.protected).toBe(true);
                done();
            });
            
            router.navigate('/dashboard');
        });
        
        test('public route should allow access without token', (done) => {
            router.afterRoute((route, path) => {
                expect(path).toBe('/login');
                expect(route.protected).toBe(false);
                done();
            });
            
            router.navigate('/login');
        });
    });
    
    describe('Token Validation', () => {
        test('isTokenExpired() should return true for expired token', () => {
            // Create an expired JWT token
            const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
            const payload = btoa(JSON.stringify({ 
                exp: Math.floor(Date.now() / 1000) - 3600, // Expired 1 hour ago
                sub: 'user123'
            }));
            const signature = 'fake-signature';
            const token = `${header}.${payload}.${signature}`;
            
            expect(router.isTokenExpired(token)).toBe(true);
        });
        
        test('isTokenExpired() should return false for valid token', () => {
            // Create a valid JWT token
            const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
            const payload = btoa(JSON.stringify({ 
                exp: Math.floor(Date.now() / 1000) + 3600, // Expires in 1 hour
                sub: 'user123'
            }));
            const signature = 'fake-signature';
            const token = `${header}.${payload}.${signature}`;
            
            expect(router.isTokenExpired(token)).toBe(false);
        });
        
        test('isTokenExpired() should handle invalid tokens', () => {
            expect(router.isTokenExpired(null)).toBe(true);
            expect(router.isTokenExpired('')).toBe(true);
            expect(router.isTokenExpired('invalid')).toBe(true);
            expect(router.isTokenExpired('a.b')).toBe(true); // Missing part
        });
    });
    
    describe('Redirect After Login', () => {
        test('redirectAfterLogin() should redirect to saved path', () => {
            localStorage.setItem('redirectAfterLogin', '/profile');
            
            router.redirectAfterLogin();
            
            expect(window.location.pathname).toBe('/profile');
            expect(localStorage.getItem('redirectAfterLogin')).toBeNull();
        });
        
        test('redirectAfterLogin() should default to dashboard', () => {
            router.redirectAfterLogin();
            
            expect(window.location.pathname).toBe('/');
        });
        
        test('redirectAfterLogin() should not redirect to login', () => {
            localStorage.setItem('redirectAfterLogin', '/login');
            
            router.redirectAfterLogin();
            
            expect(window.location.pathname).toBe('/');
        });
    });
    
    describe('Link Interception', () => {
        test('internal links should be intercepted', () => {
            const link = document.createElement('a');
            link.href = '/dashboard';
            document.body.appendChild(link);
            
            const clickEvent = new MouseEvent('click', { bubbles: true });
            let defaultPrevented = false;
            
            link.addEventListener('click', (e) => {
                if (e.defaultPrevented) defaultPrevented = true;
            });
            
            link.dispatchEvent(clickEvent);
            
            expect(defaultPrevented).toBe(true);
            document.body.removeChild(link);
        });
        
        test('external links should not be intercepted', () => {
            const link = document.createElement('a');
            link.href = 'https://example.com';
            document.body.appendChild(link);
            
            const clickEvent = new MouseEvent('click', { bubbles: true });
            let defaultPrevented = false;
            
            link.addEventListener('click', (e) => {
                if (e.defaultPrevented) defaultPrevented = true;
            });
            
            link.dispatchEvent(clickEvent);
            
            expect(defaultPrevented).toBe(false);
            document.body.removeChild(link);
        });
    });
});

// Manual test scenarios to run in browser
console.log(`
Manual Router Tests:
1. Navigate to /dashboard - should redirect to /login if not authenticated
2. Navigate to /login - should load login page (placeholder for now)
3. Set token: localStorage.setItem('accessToken', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjk5OTk5OTk5OTksInN1YiI6InVzZXIxMjMifQ.fake')
4. Navigate to /dashboard - should load dashboard
5. Click browser back button - should navigate properly
6. Clear token: localStorage.clear()
7. Navigate to /profile - should redirect to /login and save redirect path
`);