module.exports = {
  preset: 'react-native',
  testMatch: ['<rootDir>/test/**/*.test.ts', '<rootDir>/test/**/*.test.tsx'],
  testTimeout: 15000,
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?)/)',
    'sdk/typescript/dist/',
  ],
  moduleNameMapper: {
    '^@superstep/sdk/chat$': '<rootDir>/../../sdk/typescript/dist/cjs/chat/index.js',
    '^@superstep/sdk$': '<rootDir>/../../sdk/typescript/dist/cjs/index.js',
    '^(\\.{1,2}/.*)\\.js$': '$1',
  },
}
