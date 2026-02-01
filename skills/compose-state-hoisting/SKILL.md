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
2. Decide the state owner (lowest common ancestor; or a plain state holder class, or a screen-level state holder like Android ViewModel for complex UI/business logic).
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
    val coroutineScope = rememberCoroutineScope()
    
    Column {
        MessagesList(
            messages = messages,
            listState = listState,
            modifier = Modifier.weight(1f)
        )
        UserInput(
            onSend = { newMessage ->
                // Scroll to bottom when new message is sent
                coroutineScope.launch {
                    listState.animateScrollToItem(messages.size)
                }
            }
        )
    }
}
```

Plain state holder for complex UI logic:
```kotlin
class FiltersState(
    initial: Filter = Filter.All,
) {
    private var _filter by mutableStateOf(initial)
    val filter: State<Filter> = derivedStateOf { _filter }

    fun setFilter(newFilter: Filter) {
        _filter = newFilter
    }
}

@Composable
fun rememberFiltersState(initial: Filter = Filter.All): FiltersState {
    return remember { FiltersState(initial) }
}
```

Saved UI element state (Android ViewModel example):
```kotlin
// Android: ViewModel with SavedStateHandle for process death survival
class FormViewModel(private val savedStateHandle: SavedStateHandle) : ViewModel() {
    var query by savedStateHandle.saveable { mutableStateOf("") }
        private set

    fun updateQuery(value: String) {
        query = value
    }
}
// Multiplatform: Use platform-specific saved state mechanisms or libraries
// like Circuit's RetainedStateRegistry, or custom serialization solutions
```

Remember with keys for controlled state resets:
```kotlin
@Composable
fun UserProfile(userId: String) {
    // State resets when userId changes; uses immutable data structure
    var profile by remember(userId) { mutableStateOf(ProfileData()) }
    
    // Load user data for this userId
    LaunchedEffect(userId) {
        profile = fetchProfile(userId)
    }
}

data class ProfileData(
    val name: String = "",
    val bio: String = ""
)
```

Derived state for computed values:
```kotlin
@Composable
fun ShoppingCart(items: List<CartItem>) {
    // Recomputes only when items list changes
    val totalPrice by remember(items) { derivedStateOf { items.sumOf { it.price } } }
    val itemCount by remember(items) { derivedStateOf { items.size } }
    
    Text("Total: $$totalPrice ($itemCount items)")
}
```

Snapshot state collections (platform-agnostic):
```kotlin
@Composable
fun TodoList() {
    // Observable list that triggers recomposition on mutations
    val todos = remember { mutableStateListOf<Todo>() }
    
    Button(onClick = { todos.add(Todo("New task")) }) {
        Text("Add Todo")
    }
    
    LazyColumn {
        items(todos) { todo ->
            TodoItem(todo, onRemove = { todos.remove(todo) })
        }
    }
}
```

## State Hoisting Rules
- Hoist state to the lowest common ancestor of all composables that read and write it; keep it as close to consumers as possible.
- If multiple states change from the same events, hoist them together.
- Over-hoisting (e.g., hoisting to screen level when a subtree would suffice) is acceptable and safer than under-hoisting; under-hoisting breaks unidirectional flow and creates duplicate sources of truth. Over-hoisting may trigger more recompositions or lose state on navigation.
- Prefer exposing immutable state plus event callbacks from the state owner.

## Stateless vs Stateful Composables
- Provide a stateless API: `value: T` and `onValueChange: (T) -> Unit` (or more specific event lambdas).
- Keep state internal only if no other composable needs to read or change it and the UI logic is simple.
- Offer both stateful and stateless variants when useful; the stateless version is the reusable/testable one.

## Decide Where to Hoist
- **UI element state + simple UI logic**: keep internal or hoist within the UI subtree.
- **Complex UI logic**: move state and UI logic into a plain state holder class scoped to the Composition.
- **Business logic or screen UI state**: hoist to a screen-level state holder (Android: ViewModel; Multiplatform: platform-specific or library solutions like Circuit, Molecule). Do not pass screen-level state holders down the tree; inject at the screen level and pass state/events instead.
- **Deep prop drilling**: for state needed by many distant descendants (theme, user session), consider `CompositionLocal` to avoid passing parameters through many layers. Use sparingly; prefer explicit parameter passing when practical.

## Choose the Correct Lifespan
- `remember`: survives recomposition only; same instance. Use for composition-scoped objects and small internal UI state. Do not use for user input that must be preserved.
- `retain`: survives recomposition + window/configuration changes (Android: activity recreation), not process death. Use for non-serializable objects (players, caches, flows, lambdas). **Do not retain** platform-specific lifecycle objects (Android: Activity, View, Fragment, ViewModel, Context, Lifecycle). **Do not retain** objects that were already created with `remember` by the caller—`retain` and `remember` are mutually exclusive for the same object.
- `rememberSaveable` / `rememberSerializable`: survives recomposition + configuration changes + process death (Android) by saving to the platform's saved state mechanism (Android: Bundle; other platforms may vary). Use for user input or UI state that cannot be reloaded from another source. Restored objects are equal but not the same instance.

**Remember Keys**: Control when state resets by passing keys to `remember(key1, key2) { }`. State recreates when any key changes. Omit keys only when state should survive all recompositions.

## Saving UI State
- Use `rememberSaveable` for UI state hoisted in composables or plain state holders; save only minimal, small data.
- Saved state storage is limited (Android Bundle: ~1MB); do not store large objects or lists. Store IDs/keys and rehydrate from data/persistent storage.
- Android: Use `SavedStateHandle` in a ViewModel for UI element state that must survive process death; keep it small and session-scoped (not persistent app data).
- Do not save full screen UI state; rebuild it from the data layer on restoration.

## Observable Types in Compose
- Convert observable types to `State<T>` before reading in composables.
- `Flow`: use `collectAsState` (platform-agnostic, always collects) or `collectAsStateWithLifecycle` (Android only, lifecycle-aware, pauses collection when UI is not visible).
- `LiveData` (Android): use `observeAsState`.
- For custom observables, create a `State<T>` via `produceState`.

## State Callbacks (RememberObserver / RetainObserver)
- Run initialization side-effects in `onRemembered` / `onRetained`, not in constructors or remember/retain lambdas.
- Always cancel work in `onForgotten` / `onRetired`; handle `onAbandoned` for canceled compositions.
- Keep implementations private; expose safe factory functions like `rememberX()` to avoid misuse.
- Do not remember the same object twice; do not pass parameters that are already wrapped in `State<T>` to another `remember` call—this creates unnecessary nested observability.

## Common Anti-Patterns
- Storing mutable collections or mutable data classes directly as state; prefer immutable containers wrapped in `State` or use snapshot state collections (`mutableStateListOf`, `mutableStateMapOf`).
- Duplicating state in multiple owners instead of hoisting to a single source of truth.
- Mixing remember and retain for the same object; remembering/retaining objects with mismatched lifespans.
- Saving large or complex objects in `rememberSaveable`/`SavedStateHandle` (Android); save IDs and rehydrate instead.
- Computing derived values inside composables without `derivedStateOf`, causing unnecessary recompositions.

## Output Expectations
- Favor stateless composables with `value` + callbacks.
- Prefer lowest common ancestor hoisting.
- Choose lifecycle APIs intentionally; call out saving strategy explicitly.
- Keep state minimal, immutable, and observable.
