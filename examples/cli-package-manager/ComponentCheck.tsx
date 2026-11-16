import { Switch } from '@/components/ui/switch';
import { useState } from 'react';

export default function ComponentCheck() {
    const [enabled, setEnabled] = useState(false);
    const [draft, setDraft] = useState('Existing page content');

    return (
        <main className="mx-auto grid max-w-lg gap-6 p-8">
            <h1 className="text-2xl font-semibold">Component installation check</h1>
            <label className="grid gap-2">
                Draft
                <input
                    className="rounded border p-2"
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                />
            </label>
            <div className="flex items-center gap-3">
                <Switch
                    id="notifications"
                    checked={enabled}
                    onCheckedChange={setEnabled}
                />
                <label htmlFor="notifications">Notifications</label>
            </div>
            <p role="status">Notifications: {enabled ? 'on' : 'off'}</p>
            <button
                type="button"
                className="w-fit rounded border px-3 py-2"
                onClick={() => setEnabled(false)}
            >
                Reset switch
            </button>
        </main>
    );
}
