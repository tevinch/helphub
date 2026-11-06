# Choose a sheet by who owns it

When replacing many Gorhom sheets, start with the workflow each sheet belongs to. A small form owned by the current screen can remain a component with local state and callbacks. A destination that needs a route identity, navigation history or a deep link fits a native-stack screen with `presentation: 'formSheet'`.

That is a practical ownership recommendation. The Screens documentation does not establish one universal default for every sheet.

This guide addresses the four questions in [Screens discussion 5149](https://github.com/software-mansion/react-native-screens/discussions/5149). Package facts were checked on **2026-11-07** against published **4.30.1** and **5.0.0-beta.1**. Version 4.30.1 is the stable release; 5.0.0-beta.1 is a prerelease.

## 1. Choose the component or a route

| Your workflow | A useful starting point |
| --- | --- |
| Edit a draft belonging to the current screen; call its existing save callback | Keep a caller-owned `<FormSheet>` component. |
| Open a destination from a URL, preserve its identity in navigation state, or navigate to it from several screens | Give it a route and use `presentation: 'formSheet'`. |
| Require an imperative detent change while open, or Android dismissal prevention on stable 4.30.1 | Keep the existing implementation for that sheet until a compatible published API meets those requirements. |

The component does not create a navigation route for you. A route also does not require putting callback functions in route params: use shared context or a store for shared state and operations, and pass a serializable identifier in params. React Navigation recommends [JSON-serializable params for persistence and deep linking](https://reactnavigation.org/docs/params/).

For a route, the native-stack configuration is:

```tsx
<Stack.Screen
  name="EditProfile"
  component={EditProfileScreen}
  options={{
    presentation: 'formSheet',
    headerShown: false,
    sheetAllowedDetents: [0.5, 0.9],
    sheetInitialDetentIndex: 0,
  }}
/>
// Open with data such as { profileId: '42' }, rather than a callback.
```

`Stack` and the screen belong to your existing `@react-navigation/native-stack` navigator. Follow the official [form-sheet configuration and platform constraints](https://reactnavigation.org/docs/native-stack-navigator/#form-sheets), including content sizing, nested scrolling and Android limitations. These route options are separate from the component props below.

## 2. The component has its own native host

Your understanding of the relationship is correct. In both checked packages, `FormSheet` directly renders `FormSheetHostNativeComponent` (`RNSFormSheetHost`); it does not render a stack `Screen` or call navigation. Its content is supplied as normal React `children`. See the [4.30.1 implementation](https://github.com/software-mansion/react-native-screens/blob/4.30.1/src/components/gamma/modals/form-sheet/FormSheet.tsx) and [5.0.0-beta.1 implementation](https://github.com/software-mansion/react-native-screens/blob/5.0.0-beta.1/src/components/modals/form-sheet/FormSheet.tsx).

This lets the example keep `draft`, `savedName` and the save callback in the calling component. The native view/controller presentation is separate from ownership of that React state. Check any provider-dependent or navigation-dependent content in your own app before migrating it.

### Try the caller-owned example on stable 4.30.1

[CallerOwnedSheet.tsx](./CallerOwnedSheet.tsx) is a complete screen component. It keeps the draft in the caller, updates the caller's saved value on Save, and synchronizes `isOpen` to `false` after a native dismissal. The draft stays in caller state when the sheet closes. Keeping that state requires the calling screen to remain mounted.

In an existing bare React Native app using the New Architecture, with a React Native version supported by Screens 4.30.1, set this dependency in your app's `package.json`, keeping its other entries:

```json
{
  "dependencies": {
    "react-native-screens": "4.30.1"
  }
}
```

Then install the updated dependencies:

```sh
npm install
```

The [4.30.1 compatibility table](https://github.com/software-mansion/react-native-screens/blob/4.30.1/README.md#supported-react-native-version) requires React Native 0.84.0 or newer for this release line. Apply the documented native installation steps and rebuild the app; a JavaScript reload does not install native code. For Expo, use the versions supported by your SDK and recheck their capabilities before applying this exact-version example.

Copy this directory into your app as `examples/sheet-ownership`, then temporarily export the example from your `App.tsx`:

```tsx
export { default } from './examples/sheet-ownership/CallerOwnedSheet';
```

Use your app's native build scripts, commonly `npm run ios` or `npm run android`, with Metro running through `npm start`. Keep your existing entry registration and native project setup. To check the example's types from the app root:

```sh
npx tsc --project examples/sheet-ownership/tsconfig.json
```

The stable import is:

```tsx
import { FormSheet } from 'react-native-screens/experimental';
```

The [stable experimental barrel](https://github.com/software-mansion/react-native-screens/blob/4.30.1/src/experimental/index.ts) explicitly warns that this API may change without a major version change. In 5.0.0-beta.1, `FormSheet` is [exported from the package root](https://github.com/software-mansion/react-native-screens/blob/5.0.0-beta.1/src/index.tsx). Moving the export does not make that beta a stable release.

## 3. Changing the detent while the sheet is open

Neither checked published package exposes `FormSheetCommands.selectDetent`. [PR 4793](https://github.com/software-mansion/react-native-screens/pull/4793) proposes it for the component and was still open and unmerged when checked. The beta package does not contain that command either. The proposal shows ongoing work; its eventual acceptance and release date need a maintainer's answer.

`initialDetentIndex` applies when the sheet transitions from closed to open. It is not a controlled selected-detent prop. Changing it on an already open sheet does not provide the requested command. See the [stable props](https://github.com/software-mansion/react-native-screens/blob/4.30.1/src/components/gamma/modals/form-sheet/FormSheet.types.ts) and [beta props](https://github.com/software-mansion/react-native-screens/blob/5.0.0-beta.1/src/components/modals/form-sheet/FormSheet.types.ts).

If “expand, then continue dragging among all detents” is required, keep that sheet on an implementation that already supports it. Closing/reopening the sheet or temporarily replacing its detent array changes the interaction; this example does neither. It does not apply the pending patch.

## 4. Android support is version-specific

The standalone component already has an Android implementation. That does not establish complete parity with iOS:

| Standalone component capability | Published 4.30.1 | Published 5.0.0-beta.1 |
| --- | --- | --- |
| Android fractional detents | Implemented; at most 3, strictly ascending and unique | Same limit |
| Android `initialDetentIndex` | Implemented in native code, despite the `ios` annotation in these props | Implemented |
| Android `preventNativeDismiss` | Setter is a TODO/no-op | Setter and dismissal coordinator implement it |
| `selectDetent` command | Absent | Absent |

The stable Android [view manager](https://github.com/software-mansion/react-native-screens/blob/4.30.1/android/src/main/java/com/swmansion/rnscreens/gamma/modals/formsheet/FormSheetHostViewManager.kt), [detent validation](https://github.com/software-mansion/react-native-screens/blob/4.30.1/android/src/main/java/com/swmansion/rnscreens/gamma/modals/formsheet/FormSheetDetents.kt) and [behavior controller](https://github.com/software-mansion/react-native-screens/blob/4.30.1/android/src/main/java/com/swmansion/rnscreens/gamma/modals/formsheet/FormSheetBehaviorController.kt) establish those stable boundaries. Compare the beta [view manager](https://github.com/software-mansion/react-native-screens/blob/5.0.0-beta.1/android/src/main/java/com/swmansion/rnscreens/react/modals/formsheet/host/FormSheetHostViewManager.kt), [dismissal coordinator](https://github.com/software-mansion/react-native-screens/blob/5.0.0-beta.1/android/src/main/java/com/swmansion/rnscreens/core/modals/formsheet/coordinator/FormSheetNativeDismissCoordinator.kt) and [detent validation](https://github.com/software-mansion/react-native-screens/blob/5.0.0-beta.1/android/src/main/java/com/swmansion/rnscreens/core/modals/formsheet/model/FormSheetDetents.kt).

The stable Android manager also leaves `largestUndimmedDetentIndex` and `prefersScrollingExpandsWhenScrolledToEdge` unimplemented. Check every required behavior against your chosen version. For a stable-only migration requiring Android dismissal prevention, retain the existing sheet for now. The published beta is available for evaluation, with its own compatibility and device checks; it is not a promise of a future stable schedule or full platform parity.

## Validation and migration checks

The TSX file type-checks against the real published Screens 4.30.1 declarations with React Native 0.84.1, React 19.2.3, React types 19.2.0 and TypeScript 7.0.2. The route options also type-check against native-stack 7.21.0, native 7.5.1 and safe-area-context 5.8.0. Negative compilation confirms that neither the stable root export nor a `FormSheetCommands` export is available. Package source inspection supplies the version/platform comparison above.

To reproduce the declaration environment, create this `package.json` in a separate scratch directory:

```json
{
  "private": true,
  "dependencies": {
    "react": "19.2.3",
    "react-native": "0.84.1",
    "react-native-screens": "4.30.1",
    "@types/react": "19.2.0",
    "typescript": "7.0.2",
    "@react-navigation/native": "7.5.1",
    "@react-navigation/native-stack": "7.21.0",
    "react-native-safe-area-context": "5.8.0"
  }
}
```

Install from that directory, copy this example beneath it as `examples/sheet-ownership`, then run the type-check command above:

```sh
npm install --ignore-scripts
```

That scratch setup checks declarations only; the native app still needs its normal installation and build steps.

These are declaration and source checks. This example has not been run in an iOS simulator, Android emulator or the original application. They do not establish native layout, keyboard behavior or a successful app migration.

Before replacing a sheet in your app:

1. Open it, edit the name, press Save, and check that the caller displays the saved name.
2. Open it again, edit without saving, dismiss natively, then reopen. Check that the draft remains and reopening works. The native-dismiss callback must reset `isOpen`.
3. Close with the explicit button and reopen again. Drag among both detents and check the keyboard on each target platform.
4. Check any required prevention of native dismissal, scrolling, accessibility and provider-dependent content. Do not migrate a sheet whose required behavior is missing in your chosen version.
5. For a route-owned sheet, also test cold deep links and navigation Back in the real navigator.

## Optional coffee

This example is free. If it saved you time, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
