import React, { useState, useRef } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Image,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useAuth } from "../context/AuthContext";
import * as api from "../api";

const DIMENSIONS = [256, 512, 768, 1024] as const;
type Dim = (typeof DIMENSIONS)[number];

const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 60; // 2 min max

export default function GenerateScreen() {
  const { token } = useAuth();
  const [prompt, setPrompt] = useState("");
  const [width, setWidth] = useState<Dim>(512);
  const [height, setHeight] = useState<Dim>(512);
  const [steps, setSteps] = useState(4);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const pollCount = useRef(0);

  const handleGenerate = async () => {
    if (!token) return;
    if (prompt.trim().length < 3) {
      setError("Prompt must be at least 3 characters.");
      return;
    }
    setError("");
    setImageUrl(null);
    setLoading(true);
    setStatus("Submitting job…");

    try {
      const job = await api.generateImage(token, {
        prompt: prompt.trim(),
        width,
        height,
        steps,
      });

      if (job.status === "done" && job.image_url) {
        setImageUrl(`${api.API_BASE_URL}${job.image_url}`);
        setStatus("Image ready ✓");
        setLoading(false);
        return;
      }

      // Poll until done or failed
      pollCount.current = 0;
      const interval = setInterval(async () => {
        pollCount.current += 1;
        try {
          const updated = await api.pollJob(token, job.id);
          setStatus(
            updated.status === "queued"
              ? "Queued…"
              : updated.status === "running"
              ? "Generating image…"
              : updated.status
          );
          if (updated.status === "done" && updated.image_url) {
            clearInterval(interval);
            setImageUrl(`${api.API_BASE_URL}${updated.image_url}`);
            setStatus("Image ready ✓");
            setLoading(false);
          } else if (updated.status === "failed") {
            clearInterval(interval);
            setError("Generation failed. Please try again.");
            setLoading(false);
          } else if (pollCount.current >= MAX_POLLS) {
            clearInterval(interval);
            setError("Timed out waiting for result.");
            setLoading(false);
          }
        } catch {
          clearInterval(interval);
          setError("Lost connection while polling.");
          setLoading(false);
        }
      }, POLL_INTERVAL_MS);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start generation");
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.heading}>✨ Generate Image</Text>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Text style={styles.label}>Prompt</Text>
        <TextInput
          style={[styles.input, styles.textarea]}
          placeholder="A futuristic city at sunset, neon lights…"
          placeholderTextColor="#555"
          multiline
          numberOfLines={4}
          value={prompt}
          onChangeText={setPrompt}
          maxLength={500}
        />
        <Text style={styles.charCount}>{prompt.length}/500</Text>

        {/* Width */}
        <Text style={styles.label}>Width</Text>
        <View style={styles.row}>
          {DIMENSIONS.map((d) => (
            <TouchableOpacity
              key={`w-${d}`}
              style={[styles.dimBtn, width === d && styles.dimBtnActive]}
              onPress={() => setWidth(d)}
            >
              <Text
                style={[styles.dimBtnText, width === d && styles.dimBtnTextActive]}
              >
                {d}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Height */}
        <Text style={styles.label}>Height</Text>
        <View style={styles.row}>
          {DIMENSIONS.map((d) => (
            <TouchableOpacity
              key={`h-${d}`}
              style={[styles.dimBtn, height === d && styles.dimBtnActive]}
              onPress={() => setHeight(d)}
            >
              <Text
                style={[styles.dimBtnText, height === d && styles.dimBtnTextActive]}
              >
                {d}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Steps */}
        <Text style={styles.label}>Steps: {steps}</Text>
        <View style={styles.row}>
          {[1, 2, 4, 8, 20].map((s) => (
            <TouchableOpacity
              key={`s-${s}`}
              style={[styles.dimBtn, steps === s && styles.dimBtnActive]}
              onPress={() => setSteps(s)}
            >
              <Text
                style={[styles.dimBtnText, steps === s && styles.dimBtnTextActive]}
              >
                {s}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleGenerate}
          disabled={loading}
        >
          {loading ? (
            <View style={styles.row}>
              <ActivityIndicator color="#fff" />
              <Text style={[styles.buttonText, { marginLeft: 8 }]}>{status}</Text>
            </View>
          ) : (
            <Text style={styles.buttonText}>🎨 Generate</Text>
          )}
        </TouchableOpacity>

        {imageUrl ? (
          <View style={styles.resultContainer}>
            <Text style={styles.successText}>{status}</Text>
            <Image
              source={{ uri: imageUrl }}
              style={styles.resultImage}
              resizeMode="contain"
            />
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: "#0f0f0f" },
  container: { padding: 20, paddingBottom: 40 },
  heading: {
    color: "#fff",
    fontSize: 22,
    fontWeight: "700",
    marginBottom: 20,
    marginTop: 4,
  },
  label: { color: "#bbb", fontSize: 13, marginBottom: 6, marginTop: 12 },
  input: {
    backgroundColor: "#1a1a1a",
    color: "#fff",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    borderWidth: 1,
    borderColor: "#333",
  },
  textarea: { minHeight: 100, textAlignVertical: "top" },
  charCount: { color: "#555", fontSize: 11, textAlign: "right", marginTop: 4 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 4 },
  dimBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: "#1a1a1a",
    borderWidth: 1,
    borderColor: "#333",
  },
  dimBtnActive: { backgroundColor: "#7C3AED", borderColor: "#7C3AED" },
  dimBtnText: { color: "#aaa", fontSize: 13, fontWeight: "600" },
  dimBtnTextActive: { color: "#fff" },
  button: {
    backgroundColor: "#7C3AED",
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: "center",
    marginTop: 20,
  },
  buttonDisabled: { opacity: 0.7 },
  buttonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  resultContainer: { marginTop: 24, alignItems: "center" },
  successText: { color: "#4ADE80", fontSize: 14, marginBottom: 12 },
  resultImage: {
    width: "100%",
    aspectRatio: 1,
    borderRadius: 12,
    backgroundColor: "#1a1a1a",
  },
  error: {
    color: "#F87171",
    fontSize: 13,
    marginBottom: 12,
    backgroundColor: "#2d1515",
    padding: 10,
    borderRadius: 8,
  },
});
