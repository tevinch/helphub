# Find the recurring-task overview in Super Productivity

Super Productivity 20.0.0 already has an overview of recurring tasks. You can reach it without adding a filter or installing a plugin.

1. Open **Inbox** in the sidebar, or a project that has a recurring task.
2. Find its **Recurring Tasks** section below the task list.
3. Click the arrow in that section’s heading. Its tooltip is **All recurring tasks**.

You do not need to create a project: Inbox is built in and its recurring tasks are included. The UI entry is the arrow in the **Recurring Tasks** heading. That section appears when the current Inbox/project has at least one recurring configuration and the view is not customized. If the section is absent, the direct web link below still opens the overview; you do not need to enable **Schedule**.

The overview shows recurring configurations from Inbox and other active projects, with their project labels and repeat rules. The Inbox section previews Inbox’s configurations, while its arrow opens the global overview. It is not a list of every generated occurrence, or a mixture of recurring and one-off scheduled tasks. Configurations belonging to archived projects are excluded.

In the web app, you can also [open the overview directly](https://app.super-productivity.com/#/scheduled-list) in the browser where you keep your tasks.

To inspect a configuration, click its repeat rule/icon in the overview. Use **Cancel** to close the dialog without changing it.

## Check the result

A small reproducible example:

- Create one recurring task in a Home project and another in a Studio project. Give one a future start date.
- Also create an ordinary unscheduled task and a one-off task scheduled for tomorrow.
- Open **All recurring tasks**. Both recurring configurations should appear, each once, with the correct project and rule. The unscheduled and one-off controls should not appear there.
- Reopen a recurring configuration to inspect its saved rule and notes, cancel, then reload the overview. The configurations and existing task content should remain available.

Earlier cross-project scripted browser checks passed in the official web app, which displayed **20.0.0WB**, using Microsoft Edge **128.0.2739.54**. Both recurring configurations appeared once each through the arrow and direct web link, then remained after reload with their saved rules, start dates and default notes. The unscheduled task and the one-off task’s date were preserved. The 12 General feature switches, theme and dark-mode selection stayed unchanged, including **Schedule** remaining off. Desktop and mobile clients were not checked.

A separate Inbox-only browser check in the official **20.0.0WB** web app used Chrome for Testing **159.0.8154.6** and no user-created projects. Two Inbox recurrences, including a future start, appeared once each through the section arrow, repeated navigation, direct web link and reload. Their saved rules, start dates and default notes remained unchanged; ordinary task content and the one-off task’s date were preserved. General feature switches, theme and dark-mode selection stayed unchanged, with **Schedule** off. This checked the default Inbox view; customized views were not exercised.

References: [20.0.0 Inbox guide](https://github.com/super-productivity/super-productivity/blob/v20.0.0/docs/wiki/4.02-Inbox-View.md), [20.0.0 overview implementation](https://github.com/super-productivity/super-productivity/blob/v20.0.0/src/app/pages/scheduled-list-page/scheduled-list-page.component.ts), [original question](https://github.com/super-productivity/super-productivity/discussions/11643).

## Optional coffee

This guide is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
