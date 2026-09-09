/** @type {import('jest').Config} */
module.exports = {
	preset: 'ts-jest',
	testEnvironment: 'node',
	testMatch: ['**/*.test.ts'],
	// dist/ holds compiled output only — never run compiled JS through jest,
	// it would just re-test the same logic twice under a different runner.
	testPathIgnorePatterns: ['/node_modules/', '/dist/'],
};
