import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  Image,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { useAuth } from "../context/AuthContext";
import * as api from "../api";

export default function GalleryScreen() {
  const { token } = useAuth();
  const [jobs, setJobs] = useState<api.JobOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const fetchJobs = useCallback(async () => {
    if (!token) return;
    try {
      const data = await api.listJobs(token);
      setJobs(data.filter((j) => j.status === "done"));
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load gallery");
    }
  }, [token]);

  useEffect(() => {
    fetchJobs().finally(() => setLoading(false));
  }, [fetchJobs]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchJobs();
    setRefreshing(false);
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#7C3AED" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>{error}</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={fetchJobs}>
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (jobs.length === 0) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyIcon}>🖼️</Text>
        <Text style={styles.emptyText}>No images yet</Text>
        <Text style={styles.emptyHint}>
          Generate your first image in the Create tab!
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      style={styles.list}
      contentContainerStyle={styles.listContent}
      data={jobs}
      keyExtractor={(item) => item.id}
      numColumns={2}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor="#7C3AED"
        />
      }
      renderItem={({ item }) => (
        <View style={styles.card}>
          <Image
            source={{ uri: `${api.API_BASE_URL}${item.image_url}` }}
            style={styles.image}
            resizeMode="cover"
          />
          <Text style={styles.prompt} numberOfLines={2}>
            {item.prompt}
          </Text>
          <Text style={styles.date}>
            {new Date(item.created_at).toLocaleDateString()}
          </Text>
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  list: { flex: 1, backgroundColor: "#0f0f0f" },
  listContent: { padding: 12, paddingBottom: 30 },
  card: {
    flex: 1,
    margin: 4,
    backgroundColor: "#1a1a1a",
    borderRadius: 12,
    overflow: "hidden",
  },
  image: { width: "100%", aspectRatio: 1 },
  prompt: { color: "#ddd", fontSize: 11, padding: 8, lineHeight: 16 },
  date: { color: "#555", fontSize: 10, paddingHorizontal: 8, paddingBottom: 8 },
  center: {
    flex: 1,
    backgroundColor: "#0f0f0f",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { color: "#fff", fontSize: 18, fontWeight: "600", marginBottom: 8 },
  emptyHint: { color: "#666", fontSize: 13, textAlign: "center" },
  error: {
    color: "#F87171",
    fontSize: 14,
    textAlign: "center",
    marginBottom: 16,
  },
  retryBtn: {
    backgroundColor: "#7C3AED",
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 8,
  },
  retryText: { color: "#fff", fontWeight: "600" },
});
