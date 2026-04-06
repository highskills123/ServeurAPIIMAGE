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

// ─── Style presets ────────────────────────────────────────────────────────────

interface StylePreset {
  key: string;       // unique identifier for this preset card
  apiStyle: string;  // value sent to the backend as the `style` parameter
  label: string;
  emoji: string;
  prompt: string;
  negativePrompt: string;
}

const STYLE_PRESETS: StylePreset[] = [
  {
    key: "dark_gothic_warrior",
    apiStyle: "dark_gothic_rpg",
    label: "Dark Gothic",
    emoji: "🦇",
    prompt:
      "dark gothic fantasy warrior knight, haunted castle background, glowing cursed sword, tattered cloak, skull motifs, moonlit shadows",
    negativePrompt:
      "bright colors, anime, cartoon, chibi, multiple characters, busy background, low quality",
  },
  {
    key: "dark_gothic_mage",
    apiStyle: "dark_gothic_rpg",
    label: "Gothic Mage",
    emoji: "🌑",
    prompt:
      "dark gothic necromancer mage, black robes, bone staff, summoning dark magic, glowing purple runes, gothic architecture",
    negativePrompt:
      "bright colors, anime, cartoon, multiple characters, cheerful, low quality",
  },
  {
    key: "dark_gothic_creature",
    apiStyle: "dark_gothic_rpg",
    label: "Gothic Creature",
    emoji: "💀",
    prompt:
      "dark gothic undead skeleton warrior, rusted armor, glowing eye sockets, graveyard environment, fog, dark atmosphere",
    negativePrompt:
      "bright colors, cute, anime, cartoon, multiple characters, low quality",
  },
  {
    key: "pixel_art",
    apiStyle: "pixel_art",
    label: "Pixel RPG",
    emoji: "🎮",
    prompt: "RPG hero character, pixel art, 8-bit style, sword and shield",
    negativePrompt: "blurry, 3D, realistic, high resolution, multiple scenes",
  },
  {
    key: "cartoon",
    apiStyle: "cartoon",
    label: "Cartoon",
    emoji: "✏️",
    prompt: "cartoon character with sword, mobile game style, clean design",
    negativePrompt: "realistic, dark, gloomy, complex background, multiple characters",
  },
];

// ─── Grid configs ─────────────────────────────────────────────────────────────

interface GridPreset {
  label: string;
  rows: number;
  cols: number;
}

const GRID_PRESETS: GridPreset[] = [
  { label: "1×4", rows: 1, cols: 4 },
  { label: "2×4", rows: 2, cols: 4 },
  { label: "4×4", rows: 4, cols: 4 },
  { label: "2×8", rows: 2, cols: 8 },
];

const FRAME_SIZES = [64, 128, 256] as const;
type FrameSize = (typeof FRAME_SIZES)[number];

const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 90; // 3 min max (sprite sheets take longer)

// ─── Component ────────────────────────────────────────────────────────────────

export default function SpritesheetScreen() {
  const { token } = useAuth();

  const [selectedPreset, setSelectedPreset] = useState<StylePreset>(STYLE_PRESETS[0]);
  const [customPrompt, setCustomPrompt] = useState("");
  const [useCustomPrompt, setUseCustomPrompt] = useState(false);

  const [grid, setGrid] = useState<GridPreset>(GRID_PRESETS[1]); // default 2×4
  const [frameSize, setFrameSize] = useState<FrameSize>(128);

  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const pollCount = useRef(0);

  const activePrompt = useCustomPrompt ? customPrompt.trim() : selectedPreset.prompt;
  const activeNeg = useCustomPrompt ? "" : selectedPreset.negativePrompt;

  const handleGenerate = async () => {
    if (!token) return;
    if (activePrompt.length < 3) {
      setError("Prompt must be at least 3 characters.");
      return;
    }
    setError("");
    setImageUrl(null);
    setLoading(true);
    setStatus("Submitting sprite sheet job…");

    try {
      const job = await api.generateSpritesheet(token, {
        prompt: activePrompt,
        rows: grid.rows,
        cols: grid.cols,
        frame_width: frameSize,
        frame_height: frameSize,
        steps: 4,
        guidance: 0.0,
        style: selectedPreset.apiStyle,
        negative_prompt: activeNeg,
      });

      pollCount.current = 0;
      const interval = setInterval(async () => {
        pollCount.current += 1;
        try {
          const updated = await api.pollJob(token, job.id);
          setStatus(
            updated.status === "queued"
              ? `Queued… (${grid.rows * grid.cols} frames)`
              : updated.status === "running"
              ? `Generating frames… (${grid.rows * grid.cols} total)`
              : updated.status
          );
          if (updated.status === "done" && updated.image_url) {
            clearInterval(interval);
            setImageUrl(`${api.API_BASE_URL}${updated.image_url}`);
            setStatus("Sprite sheet ready ✓");
            setLoading(false);
          } else if (updated.status === "failed") {
            clearInterval(interval);
            setError(updated.image_url ?? "Generation failed. Please try again.");
            setLoading(false);
          } else if (pollCount.current >= MAX_POLLS) {
            clearInterval(interval);
            setError("Timed out waiting for sprite sheet.");
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

  const sheetWidth = grid.cols * frameSize;
  const sheetHeight = grid.rows * frameSize;

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
        <Text style={styles.heading}>🦇 Dark Gothic Sprite Sheet</Text>
        <Text style={styles.subheading}>
          RPG animation-ready sprite sheet generator
        </Text>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        {/* Style presets */}
        <Text style={styles.label}>Style Preset</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.presetRow}>
          {STYLE_PRESETS.map((preset) => (
            <TouchableOpacity
              key={preset.key}
              style={[
                styles.presetCard,
                selectedPreset === preset && styles.presetCardActive,
              ]}
              onPress={() => {
                setSelectedPreset(preset);
                setUseCustomPrompt(false);
              }}
            >
              <Text style={styles.presetEmoji}>{preset.emoji}</Text>
              <Text
                style={[
                  styles.presetLabel,
                  selectedPreset === preset && styles.presetLabelActive,
                ]}
              >
                {preset.label}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Preset prompt preview */}
        {!useCustomPrompt && (
          <View style={styles.promptPreview}>
            <Text style={styles.promptPreviewText} numberOfLines={3}>
              {selectedPreset.prompt}
            </Text>
            <TouchableOpacity onPress={() => setUseCustomPrompt(true)}>
              <Text style={styles.editLink}>✏️ Customize prompt</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Custom prompt */}
        {useCustomPrompt && (
          <View>
            <Text style={styles.label}>Custom Prompt</Text>
            <TextInput
              style={[styles.input, styles.textarea]}
              placeholder="Dark gothic warrior in full armor, battle stance…"
              placeholderTextColor="#555"
              multiline
              numberOfLines={4}
              value={customPrompt}
              onChangeText={setCustomPrompt}
              maxLength={500}
            />
            <View style={styles.rowBetween}>
              <Text style={styles.charCount}>{customPrompt.length}/500</Text>
              <TouchableOpacity onPress={() => setUseCustomPrompt(false)}>
                <Text style={styles.editLink}>← Use preset</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Grid layout */}
        <Text style={styles.label}>Grid Layout</Text>
        <View style={styles.row}>
          {GRID_PRESETS.map((g) => (
            <TouchableOpacity
              key={g.label}
              style={[styles.dimBtn, grid === g && styles.dimBtnActive]}
              onPress={() => setGrid(g)}
            >
              <Text style={[styles.dimBtnText, grid === g && styles.dimBtnTextActive]}>
                {g.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Frame size */}
        <Text style={styles.label}>Frame Size (px)</Text>
        <View style={styles.row}>
          {FRAME_SIZES.map((s) => (
            <TouchableOpacity
              key={s}
              style={[styles.dimBtn, frameSize === s && styles.dimBtnActive]}
              onPress={() => setFrameSize(s)}
            >
              <Text
                style={[styles.dimBtnText, frameSize === s && styles.dimBtnTextActive]}
              >
                {s}×{s}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Summary */}
        <View style={styles.summaryBox}>
          <Text style={styles.summaryText}>
            📐 Output: {sheetWidth}×{sheetHeight} px  •  {grid.rows * grid.cols} frames
          </Text>
          <Text style={styles.summaryText}>
            🎨 Style: {selectedPreset.label}  •  Frames: {grid.label}
          </Text>
        </View>

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleGenerate}
          disabled={loading}
        >
          {loading ? (
            <View style={styles.rowCenter}>
              <ActivityIndicator color="#fff" />
              <Text style={[styles.buttonText, { marginLeft: 8 }]}>{status}</Text>
            </View>
          ) : (
            <Text style={styles.buttonText}>🦇 Generate Sprite Sheet</Text>
          )}
        </TouchableOpacity>

        {imageUrl ? (
          <View style={styles.resultContainer}>
            <Text style={styles.successText}>{status}</Text>
            <Image
              source={{ uri: imageUrl }}
              style={[
                styles.resultImage,
                { aspectRatio: sheetWidth / sheetHeight },
              ]}
              resizeMode="contain"
            />
            <Text style={styles.dimensionHint}>
              {sheetWidth}×{sheetHeight} px • {grid.rows * grid.cols} frames • {frameSize}×{frameSize} each
            </Text>
          </View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const GOTHIC_ACCENT = "#8B1A1A"; // deep blood red – dark gothic accent
const GOTHIC_GLOW = "#C41E3A";   // crimson for active states

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: "#080808" },
  container: { padding: 20, paddingBottom: 48 },

  heading: {
    color: "#E8D5C4",
    fontSize: 22,
    fontWeight: "700",
    marginBottom: 4,
    marginTop: 4,
  },
  subheading: {
    color: "#7a6a5a",
    fontSize: 13,
    marginBottom: 20,
  },

  label: { color: "#bbb", fontSize: 13, marginBottom: 6, marginTop: 14 },

  // Preset cards
  presetRow: { marginBottom: 4 },
  presetCard: {
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: "#141414",
    borderWidth: 1,
    borderColor: "#2a2a2a",
    marginRight: 8,
    minWidth: 72,
  },
  presetCardActive: {
    backgroundColor: "#2a0808",
    borderColor: GOTHIC_GLOW,
  },
  presetEmoji: { fontSize: 20, marginBottom: 4 },
  presetLabel: { color: "#888", fontSize: 11, fontWeight: "600", textAlign: "center" },
  presetLabelActive: { color: "#E8D5C4" },

  // Prompt preview
  promptPreview: {
    backgroundColor: "#131313",
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: "#2a2a2a",
    marginTop: 8,
  },
  promptPreviewText: { color: "#999", fontSize: 12, lineHeight: 18, marginBottom: 8 },
  editLink: { color: GOTHIC_GLOW, fontSize: 12, fontWeight: "600" },

  // Input
  input: {
    backgroundColor: "#141414",
    color: "#E8D5C4",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 14,
    borderWidth: 1,
    borderColor: "#2a2a2a",
  },
  textarea: { minHeight: 90, textAlignVertical: "top" },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", marginTop: 4 },
  charCount: { color: "#555", fontSize: 11 },

  // Buttons row
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 4 },
  rowCenter: { flexDirection: "row", alignItems: "center" },
  dimBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: "#141414",
    borderWidth: 1,
    borderColor: "#2a2a2a",
  },
  dimBtnActive: { backgroundColor: GOTHIC_ACCENT, borderColor: GOTHIC_GLOW },
  dimBtnText: { color: "#888", fontSize: 13, fontWeight: "600" },
  dimBtnTextActive: { color: "#E8D5C4" },

  // Summary box
  summaryBox: {
    backgroundColor: "#0e0a0a",
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: "#2a1515",
    marginTop: 16,
    marginBottom: 4,
    gap: 4,
  },
  summaryText: { color: "#9a8a7a", fontSize: 12 },

  // Generate button
  button: {
    backgroundColor: GOTHIC_ACCENT,
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: "center",
    marginTop: 20,
    borderWidth: 1,
    borderColor: GOTHIC_GLOW,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: "#E8D5C4", fontWeight: "700", fontSize: 16 },

  // Result
  resultContainer: { marginTop: 28, alignItems: "center" },
  successText: { color: GOTHIC_GLOW, fontSize: 14, marginBottom: 12, fontWeight: "600" },
  resultImage: {
    width: "100%",
    borderRadius: 8,
    backgroundColor: "#0a0a0a",
    borderWidth: 1,
    borderColor: "#2a1515",
  },
  dimensionHint: {
    color: "#5a4a3a",
    fontSize: 11,
    marginTop: 8,
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
