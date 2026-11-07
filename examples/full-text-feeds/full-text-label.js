function filterMessage() {
  const labelId = acc.findLabel("Full-text feeds");
  if (labelId === "") {
    throw new Error("Create the Full-text feeds label first.");
  }
  if (!msg.assignLabel(labelId)) {
    throw new Error("Could not assign the Full-text feeds label.");
  }
  return Msg.Accept;
}
