export function validateRange(start, end) {
  if (!(start instanceof Date) || !(end instanceof Date) ||
      Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return 'Choose a start and an end.';
  }
  return end.getTime() > start.getTime() ? '' : 'End must be after start.';
}
export function localStamp(date) {
  const pad = n => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
