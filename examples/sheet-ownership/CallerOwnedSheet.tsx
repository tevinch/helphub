import React, { useState } from 'react';
import { Button, StyleSheet, Text, TextInput, View } from 'react-native';
import { FormSheet } from 'react-native-screens/experimental';

// For react-native-screens 4.30.1, in an existing compatible native app.
export default function CallerOwnedSheet() {
  const [isOpen, setIsOpen] = useState(false);
  const [draft, setDraft] = useState('Ada');
  const [savedName, setSavedName] = useState('Ada');

  function saveDraft() {
    setSavedName(draft);
    setIsOpen(false);
  }

  return (
    <View style={styles.screen}>
      <Text style={styles.text}>Saved name: {savedName}</Text>
      <Button title="Edit name" onPress={() => setIsOpen(true)} />

      <FormSheet
        isOpen={isOpen}
        detents={[0.5, 0.9]}
        initialDetentIndex={0}
        onNativeDismiss={() => setIsOpen(false)}>
        <View style={styles.content}>
          <Text style={styles.text}>Name</Text>
          <TextInput
            accessibilityLabel="Name draft"
            value={draft}
            onChangeText={setDraft}
            style={styles.input}
          />
          <Button title="Save" onPress={saveDraft} />
          <Button title="Close, keep draft" onPress={() => setIsOpen(false)} />
        </View>
      </FormSheet>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, justifyContent: 'center', padding: 24 },
  content: { flex: 1, backgroundColor: '#ffffff', padding: 24 },
  text: { color: '#222222', fontSize: 18, marginBottom: 12 },
  input: {
    borderWidth: 1,
    borderColor: '#666666',
    color: '#222222',
    padding: 12,
    marginBottom: 12,
  },
});
