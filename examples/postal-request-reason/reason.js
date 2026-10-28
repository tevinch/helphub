function markPostalReason(sender, originalEvent, headers) {
  if (!sender?.matches('[data-postal]')) return;
  if (originalEvent?.type === 'focusout' && originalEvent.target === sender) {
    headers['X-Postal-Reason'] = 'validate';
  } else if (originalEvent?.type === 'input' && originalEvent.target?.id === 'country') {
    headers['X-Postal-Reason'] = 'refresh';
  }
}

document.addEventListener('htmx:configRequest', event => {
  const request = event.detail;
  markPostalReason(request.elt, request.triggeringEvent, request.headers);
});

document.addEventListener('htmx:config:request', event => {
  const context = event.detail.ctx;
  markPostalReason(context.sourceElement, context.sourceEvent, context.request.headers);
});
