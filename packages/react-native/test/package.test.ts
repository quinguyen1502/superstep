describe('package boundary', () => {
  const manifest = jest.requireActual('../package.json') as {
    name: string
    version: string
    peerDependencies: Record<string, string>
    dependencies?: Record<string, string>
  }

  test('stays a separate native package on the SDK and React Native peers', () => {
    expect(manifest.name).toBe('@superstep/react-native')
    expect(manifest.version).toBe('0.1.0')
    expect(manifest.peerDependencies['react-native']).toBe('>=0.73')
    expect(manifest.peerDependencies['@superstep/sdk']).toBe('^0.2.0')
    expect(manifest.peerDependencies['react-dom']).toBeUndefined()
    expect(manifest.dependencies?.['react-dom']).toBeUndefined()
    expect(JSON.stringify(manifest)).not.toContain('react-dom')
  })
})
