# Back up a BESSER project before freeing browser storage

The BESSER Web Modeling Editor saves local projects in your browser. At a warning such as **4.3 MB / 5 MB**, you can make room by exporting a project you no longer need open and deleting that project's local copy. Keep the exported JSON outside the editor.

## Export and check one project

1. In the editor's top bar, choose **File → Open Project…** and open an older project you can archive. In this example, it is `Archive_Catalog`. Your current project, `Current_Catalog`, stays in the project list.
2. In the older project, choose **File → Export Project…**. Under **Multiple Diagrams**, check every diagram type you want to keep. The dialog initially checks **Class Diagram** when it is available. For a project with both class and state machine diagrams, check **State Machine Diagram** too. Choose **Export as JSON** in that section and save the downloaded file.
   You can use this synthetic archive to practice the next step. [Download the sample project](archive-catalog.example.json)

3. In a fresh browser profile, open the same editor. From the welcome screen, choose **More options → Import Project**, then click the file area and select the downloaded JSON. Open each diagram you need and check its contents. In the example, this means checking the `ArchivedStock` class in **Archived stock record** and the `Discontinued` state in **Archived stock lifecycle**. Keep your original profile open so that the check leaves its project list alone.

If the editor already reported a failed save, capture any unsaved work before switching projects. Export can use the last saved project data. Copy any separate files you need, such as a downloaded code archive, alongside your model backup.

## Free space and continue editing

1. Back in your original profile, reopen `Current_Catalog` using **File → Open Project…**. Open **File → Open Project…** again and hover over the `Archive_Catalog` card to show its trash button.
2. Select the trash button, check the project name in the confirmation, and choose **Delete**. You can cancel if the name differs or you still need to check the export.
3. Reopen your current project, make and save your next edit, and reload to check that it survived. Keep the older project's JSON for later. Importing the archive back into your original profile will consume storage there again.

A browser test exercised these steps with two disposable projects in the hosted editor, using version 8.9.4. A JSON export and import preserved both populated diagram types. Cancelling deletion kept both projects. Confirming deletion removed the archived project, and the current project reopened with its original class and a new project name after another save and reload.

The official project guide covers import and export. The editor change under review adds a quicker way to reach the storage controls. [Project guide](https://besser.readthedocs.io/projects/besser-web-modeling-editor/en/stable/user-guide/projects.html) · [Editor change](https://github.com/BESSER-PEARL/BESSER-Web-Modeling-Editor/pull/298)

## Optional coffee

If this example saved you time and you'd like to buy me a coffee, thank you. It is entirely optional.

- **USDC / SOL · Solana**: `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base**: `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20)**: `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
