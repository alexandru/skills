# Compose State Guidance (Condensed)

## Core Concepts
- State is any value that can change over time; Compose is declarative, so UI updates only when composables receive new state, triggering recomposition.
- State should be observable (`State<T>`, `MutableState<T>`). Avoid mutable collections/data classes as state holders; prefer immutable values wrapped in `State`.

## State Hoisting
- Hoist state to the lowest common ancestor of all readers/writers.
- State down, events up (unidirectional data flow).
- Hoist together when multiple values change from the same events.

## Where State Lives
- Simple UI element state: keep local to the composable.
- Complex UI logic: move to a plain state holder class scoped to the composition.
- Business logic/screen UI state: hoist to a screen-level state holder (Android: ViewModel). Inject at screen level; do not pass ViewModel down the tree.

## Lifespans
- `remember`: recomposition only; same instance; best for small internal state and avoiding expensive work.
- `retain`: survives configuration change; no process death; use for non-serializable objects; avoid retaining Activity/View/Fragment/Context/Lifecycle/ViewModel.
- `rememberSaveable` / `rememberSerializable`: survives process death by saving to Bundle; restored values are equal but not the same instance.

## Saving
- Save small, transient UI state (input, scroll, selection). Store IDs/keys; rehydrate heavy data.
- `SavedStateHandle` (ViewModel): use for small UI element state; do not store full screen UI state.

## Observables
- `Flow`: `collectAsStateWithLifecycle` (Android) or `collectAsState` (MPP).
- `LiveData`: `observeAsState`.
- Custom observable: `produceState`.

## State Callbacks
- Initialize work in `onRemembered` / `onRetained`, not constructors.
- Cancel in `onForgotten` / `onRetired`; handle `onAbandoned` for canceled compositions.
- Do not remember objects twice; do not remember parameters already remembered by the caller.
