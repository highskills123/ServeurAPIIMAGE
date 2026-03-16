import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { useAuth } from "../context/AuthContext";

interface Props {
  onSwitch: () => void;
}

export default function LoginScreen({ onSwitch }: Props) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async () => {
    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await login(email, password);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.logo}>🎨 PixelForge AI</Text>
        <Text style={styles.tagline}>Generate stunning images with AI</Text>

        <View style={styles.card}>
          <Text style={styles.title}>Sign In</Text>

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Text style={styles.label}>Email</Text>
          <TextInput
            style={styles.input}
            placeholder="you@example.com"
            placeholderTextColor="#666"
            autoCapitalize="none"
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
          />

          <Text style={styles.label}>Password</Text>
          <TextInput
            style={styles.input}
            placeholder="••••••••"
            placeholderTextColor="#666"
            secureTextEntry
            value={password}
            onChangeText={setPassword}
          />

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Sign In</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity style={styles.link} onPress={onSwitch}>
            <Text style={styles.linkText}>
              Don&apos;t have an account?{" "}
              <Text style={styles.linkBold}>Sign Up</Text>
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: "#0f0f0f" },
  container: {
    flexGrow: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  logo: { fontSize: 36, marginBottom: 8 },
  tagline: { color: "#aaa", fontSize: 14, marginBottom: 32, textAlign: "center" },
  card: {
    width: "100%",
    maxWidth: 400,
    backgroundColor: "#1a1a1a",
    borderRadius: 16,
    padding: 24,
  },
  title: { color: "#fff", fontSize: 22, fontWeight: "700", marginBottom: 16 },
  label: { color: "#bbb", fontSize: 13, marginBottom: 4 },
  input: {
    backgroundColor: "#252525",
    color: "#fff",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "#333",
  },
  button: {
    backgroundColor: "#7C3AED",
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 4,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  link: { marginTop: 16, alignItems: "center" },
  linkText: { color: "#aaa", fontSize: 14 },
  linkBold: { color: "#7C3AED", fontWeight: "700" },
  error: {
    color: "#F87171",
    fontSize: 13,
    marginBottom: 12,
    backgroundColor: "#2d1515",
    padding: 10,
    borderRadius: 8,
  },
});
