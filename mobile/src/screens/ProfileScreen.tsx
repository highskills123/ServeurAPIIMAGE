import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
} from "react-native";
import { useAuth } from "../context/AuthContext";

export default function ProfileScreen() {
  const { user, logout } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  const handleLogout = () => {
    Alert.alert("Sign Out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        style: "destructive",
        onPress: async () => {
          setSigningOut(true);
          await logout();
        },
      },
    ]);
  };

  const planColors: Record<string, string> = {
    free: "#6B7280",
    starter: "#3B82F6",
    pro: "#8B5CF6",
    business: "#F59E0B",
  };

  const planColor = planColors[user?.plan ?? "free"] ?? "#6B7280";

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>
          {user?.email?.[0]?.toUpperCase() ?? "?"}
        </Text>
      </View>

      <Text style={styles.email}>{user?.email}</Text>

      <View style={[styles.badge, { backgroundColor: planColor + "22", borderColor: planColor }]}>
        <Text style={[styles.badgeText, { color: planColor }]}>
          {(user?.plan ?? "free").toUpperCase()} PLAN
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        <View style={styles.row}>
          <Text style={styles.rowLabel}>Email</Text>
          <Text style={styles.rowValue}>{user?.email}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.rowLabel}>Plan</Text>
          <Text style={[styles.rowValue, { color: planColor }]}>
            {user?.plan ?? "free"}
          </Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.rowLabel}>User ID</Text>
          <Text style={styles.rowValue}>#{user?.id}</Text>
        </View>
      </View>

      <TouchableOpacity
        style={[styles.logoutBtn, signingOut && { opacity: 0.6 }]}
        onPress={handleLogout}
        disabled={signingOut}
      >
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f0f0f" },
  content: { padding: 24, alignItems: "center" },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "#7C3AED",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 20,
    marginBottom: 12,
  },
  avatarText: { color: "#fff", fontSize: 32, fontWeight: "700" },
  email: { color: "#fff", fontSize: 16, marginBottom: 10 },
  badge: {
    paddingHorizontal: 14,
    paddingVertical: 5,
    borderRadius: 20,
    borderWidth: 1,
    marginBottom: 32,
  },
  badgeText: { fontSize: 12, fontWeight: "700", letterSpacing: 1 },
  section: {
    width: "100%",
    backgroundColor: "#1a1a1a",
    borderRadius: 14,
    padding: 4,
    marginBottom: 24,
  },
  sectionTitle: {
    color: "#888",
    fontSize: 12,
    fontWeight: "600",
    letterSpacing: 0.5,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 4,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderTopWidth: 1,
    borderTopColor: "#252525",
  },
  rowLabel: { color: "#bbb", fontSize: 14 },
  rowValue: { color: "#fff", fontSize: 14, fontWeight: "500" },
  logoutBtn: {
    width: "100%",
    backgroundColor: "#2d1515",
    borderWidth: 1,
    borderColor: "#7f1d1d",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  logoutText: { color: "#F87171", fontWeight: "700", fontSize: 15 },
});
