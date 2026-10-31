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

module.exports = (env, argv) => ({
  entry: './index.web.js',
  output: {
    path: path.resolve(__dirname, 'dist/web'),
    publicPath: process.env.PUBLIC_PATH || '/',
  },
  resolve: {
    alias: {
      'react-native$': 'react-native-web',
    },
    extensions: ['.web.tsx', '.web.ts', '.web.js', '.tsx', '.ts', '.js', '.json'],
  },
  module: {
    rules: [
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
        // Keep the Ionicons.ttf name so web/index.html's @font-face can point at it.
        generator: {filename: '[name][ext]'},
      },
    ],
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: path.resolve(__dirname, 'web/index.html'),
    }),
    new webpack.DefinePlugin({
      __DEV__: JSON.stringify(argv.mode !== 'production'),
      'process.env.NODE_ENV': JSON.stringify(argv.mode),
    }),
  ],
  devServer: {
    static: path.resolve(__dirname, 'dist/web'),
    port: 8080,
  },
});
