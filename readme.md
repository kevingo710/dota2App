## Screenshots

<div style="display: flex; flex-direction: 'row';">
<img src="./screenshots/heroScreenshot.png" width=30%>
</div>

## Demo

<div style="display: flex; flex-direction: 'row';">
<img src="./screenshots/heroeList.gif" width=30%>

</div>


## To run this app

Requirements: Node >= 22.11, Yarn 1, JDK 17 (Android), Xcode + CocoaPods (iOS).

```sh
yarn install
cd ios && bundle install && bundle exec pod install && cd ..
yarn ios      # or: yarn android
```

### Better screenshots remove shadow

´defaults write com.apple.screencapture disable-shadow -bool TRUE; killall SystemUIServer´ 
## Architecture

Clean Architecture with an [InversifyJS](https://inversify.io) container (`reflect-metadata` + legacy decorators via Babel):

```
src/
  domain/          entities, repository interfaces, use cases (no framework imports)
  data/            DTOs, mappers, data sources, repository implementations
  infrastructure/  HttpClient (axios)
  core/di/         TYPES tokens, ContainerModules, container, DIProvider/useInjection
  core/query/      TanStack Query client (AppState-driven refetch on focus)
  presentation/    screens, navigation, hooks, theme
```

Dependencies point inwards: `presentation -> domain <- data -> infrastructure`. Bindings live in `src/core/di/modules.ts`; components resolve use cases with `useInjection(TYPES.X)` and call them from TanStack Query hooks (`useQuery({queryKey, queryFn: () => useCase.execute()})`), and tests can `container.rebind(...)` any dependency.
