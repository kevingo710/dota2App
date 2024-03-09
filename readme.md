## Screenshots

<div style="display: flex; flex-direction: 'row';">
<img src="./screenshots/heroScreenshot.png" width=30%>
</div>

## Demo

<div style="display: flex; flex-direction: 'row';">
<img src="./screenshots/heroeList.gif" width=30%>

</div>


## To run this app
´´´yarn install´´´

´´´ios/pod install´´

### Legacy versions react-native on xCode 14
Fix Yoga |
RCT-Folly

### This command is required by use legacy react-native & node version
NODE_OPTIONS=--openssl-legacy-provider 


### Better screenshots remove shadow

´defaults write com.apple.screencapture disable-shadow -bool TRUE; killall SystemUIServer´ 