import React, { useCallback, useEffect, useRef } from 'react';
import { useGridDate } from 'ag-grid-react';
import flatpickr from 'flatpickr';

export function DatePicker({ date, onDateChange, onFocusIn }) {
  const wrapper = useRef(null);
  const input = useRef(null);
  const picker = useRef(null);

  useEffect(() => {
    const instance = flatpickr(wrapper.current, {
      wrap: true,
      dateFormat: 'd/m/Y',
      allowInput: true,
      disableMobile: true,
      onReady: (_dates, _text, calendar) => {
        calendar.calendarContainer.classList.add('ag-custom-component-popup');
      },
      onChange: ([selected]) => onDateChange(selected ?? null),
    });
    picker.current = instance;
    return () => {
      instance.destroy();
      picker.current = null;
    };
  }, [onDateChange]);

  useEffect(() => {
    const instance = picker.current;
    if (instance && instance.selectedDates[0]?.getTime() !== date?.getTime()) {
      instance.setDate(date ?? [], false);
    }
  }, [date, onDateChange]);

  const setInputPlaceholder = useCallback(value => { input.current.placeholder = value; }, []);
  const setInputAriaLabel = useCallback(value => { input.current.setAttribute('aria-label', value); }, []);
  const setDisabled = useCallback(value => {
    input.current.disabled = value;
    wrapper.current.querySelector('button').disabled = value;
  }, []);
  useGridDate({ setInputPlaceholder, setInputAriaLabel, setDisabled });

  return (
    <div className="date-picker" ref={wrapper}>
      <input
        ref={input}
        type="text"
        placeholder="dd/mm/yyyy"
        data-input
        className="ag-input-field-input"
        onFocus={() => onFocusIn?.()}
      />
      <button type="button" aria-label="Clear date" data-clear>Clear</button>
    </div>
  );
}
