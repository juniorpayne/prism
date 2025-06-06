module.exports = {
    env: {
        browser: true,
        es2021: true,
        node: true
    },
    extends: [
        'eslint:recommended'
    ],
    parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module'
    },
    rules: {
        // Code quality
        'no-console': 'warn',
        'no-debugger': 'error',
        'no-unused-vars': ['error', { 'argsIgnorePattern': '^_' }],
        
        // Best practices
        'eqeqeq': ['error', 'always'],
        'curly': ['error', 'all'],
        'no-eval': 'error',
        'no-implied-eval': 'error',
        
        // Style (basic formatting)
        'indent': ['error', 4],
        'quotes': ['error', 'single'],
        'semi': ['error', 'always'],
        'comma-dangle': ['error', 'never'],
        
        // Modern JS practices
        'prefer-const': 'error',
        'no-var': 'error',
        'prefer-arrow-callback': 'error'
    },
    globals: {
        // Browser globals
        'window': 'readonly',
        'document': 'readonly',
        'console': 'readonly',
        'fetch': 'readonly',
        
        // Custom globals for our app
        'API': 'readonly',
        'Utils': 'readonly'
    }
};