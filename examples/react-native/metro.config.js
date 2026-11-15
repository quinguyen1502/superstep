const path = require('path')
const { getDefaultConfig } = require('expo/metro-config')

const config = getDefaultConfig(__dirname)
const sdk = path.resolve(__dirname, '../../sdk/typescript')
const native = path.resolve(__dirname, '../../packages/react-native')
config.watchFolders = [sdk, native]
config.resolver.nodeModulesPaths = [path.resolve(__dirname, 'node_modules')]
config.resolver.extraNodeModules = {
  '@superstep/sdk': sdk,
  '@superstep/react-native': native,
}
module.exports = config
