import {
  createContext,
  PropsWithChildren,
  useContext,
  useState,
} from "react";

import type { DemoRunRequest, DemoRunResponse } from "./types";

interface SessionContextValue {
  draft: DemoRunRequest | null;
  result: DemoRunResponse | null;
  setDraft: (draft: DemoRunRequest) => void;
  setResult: (result: DemoRunResponse) => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: PropsWithChildren) {
  const [draft, setDraft] = useState<DemoRunRequest | null>(null);
  const [result, setResult] = useState<DemoRunResponse | null>(null);

  return (
    <SessionContext.Provider value={{ draft, result, setDraft, setResult }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used inside SessionProvider");
  }
  return context;
}
