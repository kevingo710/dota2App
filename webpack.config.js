const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const webpack = require('webpack');

// Packages under node_modules that ship untranspiled ES/TS and must go through babel.
const TRANSPILED_MODULES = [
  'react-native-vector-icons',
  '@react-native-vector-icons',
  '@react-navigation',
  'react-native-screens',
  'react-native-safe-area-context',
  '@legendapp/list',
];

module.exports = (env, argv) => {
  const mode = argv.mode || 'development';
  return {
    entry: './index.web.js',
    output: {
      path: path.resolve(__dirname, 'dist/web'),
      publicPath: process.env.PUBLIC_PATH || '/',
    },
    resolve: {
      alias: {
        'react-native$': 'react-native-web',
      },
      extensions: [
        '.web.tsx',
        '.web.ts',
        '.web.js',
        '.tsx',
        '.ts',
        '.js',
        '.json',
      ],
    },
    module: {
      rules: [
        {
          // ESM packages require full paths; babel-plugin-react-native-web
          // rewrites imports to extensionless react-native-web/dist/exports/*.
          test: /\.m?js$/,
          resolve: {fullySpecified: false},
        },
        {
          test: /\.(js|jsx|ts|tsx)$/,
          exclude: new RegExp(
            `node_modules/(?!(${TRANSPILED_MODULES.join('|')})/)`,
          ),
          // babel.config.js decides the web plugin via the babel-loader caller.
          use: 'babel-loader',
        },
        {
          test: /\.(ttf|png)$/i,
          type: 'asset/resource',
          generator: {filename: 'assets/[name].[contenthash:8][ext]'},
        },
      ],
    },
    plugins: [
      new HtmlWebpackPlugin({
        template: path.resolve(__dirname, 'web/index.html'),
      }),
      new webpack.DefinePlugin({
        __DEV__: JSON.stringify(mode !== 'production'),
        'process.env.NODE_ENV': JSON.stringify(mode),
      }),
    ],
    // Optional requires inside try/catch in vector-icons (expo-font, get-image):
    // absent on purpose, the static Ionicons set needs neither.
    ignoreWarnings: [{module: /@react-native-vector-icons\/common/}],
    // A demo bundle; react-native-web alone is over the 244 KiB hint.
    performance: {hints: false},
    devServer: {
      static: path.resolve(__dirname, 'dist/web'),
      port: 8080,
    },
  };
};
