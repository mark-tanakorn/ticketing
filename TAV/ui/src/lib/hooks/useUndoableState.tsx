import { useCallback, useReducer } from 'react';
import { produceWithPatches, applyPatches, Patch, enablePatches } from 'immer';

type PatchChange = { patches: Patch[]; inversePatches: Patch[] };

export interface UndoableStateApi<T> {
  present: T;
  pushSnapshot(snapshot: T): void;
  pushProducer(producer: (draft: T) => void): void;
  replace(snapshot: T): void;
  undo(): void;
  redo(): void;
  canUndo: boolean;
  canRedo: boolean;
}

export function useUndoableState<T extends object>(initial: T, maxHistory = 100): UndoableStateApi<T> {
  // Ensure immer 'patches' plugin is enabled. Guard against multiple calls.
  try {
    // @ts-ignore - enablePatches is available at runtime after import
    if (!(globalThis as any).__immer_patches_enabled) {
      enablePatches();
      (globalThis as any).__immer_patches_enabled = true;
    }
  } catch (err) {
    // ignore – enablePatches may already be initialized or not available in some environments
  }
  type State = { past: PatchChange[]; present: T; future: PatchChange[] };
  type Action =
    | { type: 'PUSH_PRODUCER'; producer: (draft: T) => void }
    | { type: 'PUSH_SNAPSHOT'; snapshot: T }
    | { type: 'UNDO' }
    | { type: 'REDO' }
    | { type: 'REPLACE'; snapshot: T };

  const initialState: State = { past: [], present: initial, future: [] };

  function reducer(state: State, action: Action): State {
    switch (action.type) {
      case 'PUSH_PRODUCER': {
        const t0 = Date.now();
        const [nextState, patches, inversePatches] = produceWithPatches(state.present, action.producer);
        if (process.env.NODE_ENV !== 'production') console.debug('[undo] PUSH_PRODUCER', patches?.length || 0, 'patches', 'time', Date.now() - t0);
        if (!patches || patches.length === 0) return state;
        const change: PatchChange = { patches, inversePatches };
        const past = [...state.past, change];
        const capped = past.length > maxHistory ? past.slice(past.length - maxHistory) : past;
        return { past: capped, present: nextState, future: [] };
      }
      case 'PUSH_SNAPSHOT': {
        // Compute patches by replacing present with the snapshot via a producer that returns the snapshot
        const [nextState, patches, inversePatches] = produceWithPatches(state.present, () => action.snapshot as T);
        if (!patches || patches.length === 0) return state;
        const change: PatchChange = { patches, inversePatches };
        const past = [...state.past, change];
        const capped = past.length > maxHistory ? past.slice(past.length - maxHistory) : past;
        return { past: capped, present: nextState, future: [] };
      }
      case 'UNDO': {
        if (process.env.NODE_ENV !== 'production') console.debug('[undo] UNDO');
        if (state.past.length === 0) return state;
        const last = state.past[state.past.length - 1];
        const newPast = state.past.slice(0, state.past.length - 1);
        const prevState = applyPatches(state.present, last.inversePatches);
        return { past: newPast, present: prevState, future: [last, ...state.future] };
      }
      case 'REDO': {
        if (process.env.NODE_ENV !== 'production') console.debug('[undo] REDO');
        if (state.future.length === 0) return state;
        const nextChange = state.future[0];
        const newFuture = state.future.slice(1);
        const nextState = applyPatches(state.present, nextChange.patches);
        return { past: [...state.past, nextChange], present: nextState, future: newFuture };
      }
      case 'REPLACE': {
        return { past: [], present: action.snapshot, future: [] };
      }
      default:
        return state;
    }
  }

  const [state, dispatch] = useReducer(reducer, initialState);

  const pushProducer = useCallback((producer: (draft: T) => void) => {
    dispatch({ type: 'PUSH_PRODUCER', producer });
  }, []);

  const pushSnapshot = useCallback((snapshot: T) => {
    dispatch({ type: 'PUSH_SNAPSHOT', snapshot });
  }, []);

  const replace = useCallback((snapshot: T) => dispatch({ type: 'REPLACE', snapshot }), []);
  const undo = useCallback(() => dispatch({ type: 'UNDO' }), []);
  const redo = useCallback(() => dispatch({ type: 'REDO' }), []);

  return {
    present: state.present,
    pushSnapshot,
    pushProducer,
    replace,
    undo,
    redo,
    canUndo: state.past.length > 0,
    canRedo: state.future.length > 0,
  };
}
