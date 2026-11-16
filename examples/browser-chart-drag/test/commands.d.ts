declare module '@vitest/browser/context' {
  interface BrowserCommands {
    moveToLabel(label: string): Promise<void>;
    moveOutside(): Promise<void>;
    press(): Promise<void>;
    release(): Promise<void>;
  }
}

export {};
