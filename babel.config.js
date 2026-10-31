module.exports = function (api) {
  // babel-loader (webpack) gets the react-native-web alias; Metro and Jest do not.
  const isWeb = api.caller(c => c && c.name === 'babel-loader');
  api.cache.using(() => isWeb);

  return {
    presets: ['module:@react-native/babel-preset'],
    plugins: [
      'babel-plugin-transform-typescript-metadata',
      ['@babel/plugin-proposal-decorators', {legacy: true}],
      [
        'module:react-native-dotenv',
        {
          moduleName: '@env',
          path: '.env',
        },
      ],
      ...(isWeb ? [['babel-plugin-react-native-web', {commonjs: false}]] : []),
    ],
  };
};
