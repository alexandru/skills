---
name: compose-state-hoisting
description: Compose state management with a strong state-hoisting preference for Kotlin Compose (Android, Multiplatform, Compose for Web). Use for refactors or new UI that needs clear state ownership, unidirectional data flow, saved state decisions, or guidance on remember/retain/rememberSaveable/rememberSerializable, and for designing stateless composables with event callbacks.
---

# Compose State Hoisting

## Overview
Apply state hoisting and unidirectional data flow to Compose UIs, choosing the right state owner, lifespan, and saving strategy.

For condensed reference, see `references/compose-state-guidance.md`.

## Workflow
1. Identify the state and the logic that reads/writes it.
2. Decide the state owner (lowest common ancestor; or a state holder/ViewModel for complex UI/business logic).
3. Choose the lifespan API (remember/retain/rememberSaveable/rememberSerializable) based on how long it must survive.
4. Make UI composables stateless: pass `value` and event callbacks; state goes down, events go up.
5. Decide what must be saved and how (rememberSaveable, SavedStateHandle, or platform storage).
6. Verify that state and callbacks are not duplicated or leaked.

## Minimal Patterns (Copy/Adapt)

Stateless + stateful pair (hoisting):
```kotlin
@Composable
fun Counter(count: Int, onIncrement: () -> Unit) {
    Column {
        Text("Count: $count")
        Button(onClick = onIncrement) {
            Text("Increment")
        }
    }
}

@Composable
fun CounterScreen() {
    var count by remember { mutableStateOf(0) }
    Counter(count = count, onIncrement = { count++ })
}
```

Lowest common ancestor hoisting:
```kotlin
@Composable
fun ConversationScreen(messages: List<Message>) {
    val listState = rememberLazyListState()
    MessagesList(messages = messages, listState = listState)
    UserInput(onSend = { /* apply UI logic to listState */ })
}
```

Plain state holder for complex UI logic:
```kotlin
class FiltersState(
    initial: Filter = Filter.All,
) {
    var filter by mutableStateOf(initial)
        private set

    fun setFilter(newFilter: Filter) {
        filter = newFilter
    }
}

@Composable
fun rememberFiltersState(initial: Filter = Filter.All): FiltersState {
    return remember { FiltersState(initial) }
}
```

Saved UI element state in ViewModel:
```kotlin
class FormViewModel(private val savedStateHandle: SavedStateHandle) : ViewModel() {
    var query by savedStateHandle.saveable { mutableStateOf("") }
        private set

    fun updateQuery(value: String) {
        query = value
    }
}
```

## State Hoisting Rules
- Hoist state to the lowest common ancestor of all composables that read and write it; keep it as close to consumers as possible.
- If multiple states change from the same events, hoist them together.
- Over-hoisting is acceptable; under-hoisting breaks unidirectional flow.
- Prefer exposing immutable state plus event callbacks from the state owner.

## Stateless vs Stateful Composables
- Provide a stateless API: `value: T` and `onValueChange: (T) -> Unit` (or more specific event lambdas).
- Keep state internal only if no other composable needs to read or change it and the UI logic is simple.
- Offer both stateful and stateless variants when useful; the stateless version is the reusable/testable one.

## Decide Where to Hoist
- **UI element state + simple UI logic**: keep internal or hoist within the UI subtree.
- **Complex UI logic**: move state and UI logic into a plain state holder class scoped to the Composition.
- **Business logic or screen UI state**: hoist to a screen-level state holder (Android: ViewModel). Do not pass ViewModel instances down the tree; inject at the screen level and pass state/events instead.

## Choose the Correct Lifespan
- `remember`: survives recomposition only; same instance. Use for composition-scoped objects and small internal UI state. Do not use for user input.
- `retain`: survives recomposition + activity recreation (config change), not process death. Use for non-serializable objects (players, caches, flows, lambdas). Do not retain objects with shorter lifespans (Activity, View, Fragment, ViewModel, Context, Lifecycle). Do not retain objects that were already remembered.
- `rememberSaveable` / `rememberSerializable`: survives recomposition + activity recreation + process death by saving to Bundle. Use for user input or UI state that cannot be reloaded from another source. Restored objects are equal but not the same instance.

## Saving UI State
- Use `rememberSaveable` for UI state hoisted in composables or plain state holders; save only minimal, small data.
- Bundle size is limited; do not store large objects or lists. Store IDs/keys and rehydrate from data/persistent storage.
- Use `SavedStateHandle` in a ViewModel for UI element state that must survive process death; keep it small and transient.
- Do not save full screen UI state in `SavedStateHandle`; rebuild it from the data layer.

## Observable Types in Compose
- Convert observable types to `State<T>` before reading in composables.
- Android-specific: prefer `collectAsStateWithLifecycle` for `Flow`.
- Multiplatform/Web: use `collectAsState` (platform-agnostic).
- For custom observables, create a `State<T>` via `produceState`.

## State Callbacks (RememberObserver / RetainObserver)
- Run initialization side-effects in `onRemembered` / `onRetained`, not in constructors or remember/retain lambdas.
- Always cancel work in `onForgotten` / `onRetired`; handle `onAbandoned` for canceled compositions.
- Keep implementations private; expose safe factory functions like `rememberX()` to avoid misuse.
- Do not remember the same object twice; do not remember inputs that are already remembered by the caller.

## Common Anti-Patterns
- Storing mutable collections or mutable data classes directly as state; prefer immutable containers wrapped in `State`.
- Duplicating state in multiple owners instead of hoisting to a single source of truth.
- Remembering/retaining objects with mismatched lifespans or retaining remembered objects.
- Saving large or complex objects in `rememberSaveable`/`SavedStateHandle`.

## Output Expectations
- Favor stateless composables with `value` + callbacks.
- Prefer lowest common ancestor hoisting.
- Choose lifecycle APIs intentionally; call out saving strategy explicitly.
- Keep state minimal, immutable, and observable.
