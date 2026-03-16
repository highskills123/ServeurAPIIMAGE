import React, { useState } from "react";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { GestureHandlerRootView } from "react-native-gesture-handler";

import { AuthProvider, useAuth } from "./src/context/AuthContext";
import LoginScreen from "./src/screens/LoginScreen";
import SignupScreen from "./src/screens/SignupScreen";
import GenerateScreen from "./src/screens/GenerateScreen";
import GalleryScreen from "./src/screens/GalleryScreen";
import ProfileScreen from "./src/screens/ProfileScreen";

// ─── Navigators ───────────────────────────────────────────────────────────────

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function AppTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: "#111" },
        headerTintColor: "#fff",
        tabBarStyle: {
          backgroundColor: "#111",
          borderTopColor: "#222",
        },
        tabBarActiveTintColor: "#7C3AED",
        tabBarInactiveTintColor: "#666",
      }}
    >
      <Tab.Screen
        name="Create"
        component={GenerateScreen}
        options={{
          title: "Create",
          tabBarLabel: "Create",
          tabBarIcon: ({ color }) => (
            <Text style={{ fontSize: 18, color }}>✨</Text>
          ),
        }}
      />
      <Tab.Screen
        name="Gallery"
        component={GalleryScreen}
        options={{
          title: "Gallery",
          tabBarLabel: "Gallery",
          tabBarIcon: ({ color }) => (
            <Text style={{ fontSize: 18, color }}>🖼️</Text>
          ),
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          title: "Profile",
          tabBarLabel: "Profile",
          tabBarIcon: ({ color }) => (
            <Text style={{ fontSize: 18, color }}>👤</Text>
          ),
        }}
      />
    </Tab.Navigator>
  );
}

// ─── Auth Gate ────────────────────────────────────────────────────────────────

function RootNavigator() {
  const { token, loading } = useAuth();
  const [showSignup, setShowSignup] = useState(false);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#7C3AED" />
      </View>
    );
  }

  if (!token) {
    return (
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {showSignup ? (
          <Stack.Screen name="Signup">
            {() => <SignupScreen onSwitch={() => setShowSignup(false)} />}
          </Stack.Screen>
        ) : (
          <Stack.Screen name="Login">
            {() => <LoginScreen onSwitch={() => setShowSignup(true)} />}
          </Stack.Screen>
        )}
      </Stack.Navigator>
    );
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Main" component={AppTabs} />
    </Stack.Navigator>
  );
}

// ─── Root ─────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <GestureHandlerRootView style={styles.root}>
      <SafeAreaProvider>
        <AuthProvider>
          <NavigationContainer>
            <StatusBar style="light" />
            <RootNavigator />
          </NavigationContainer>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#0f0f0f" },
  loadingContainer: {
    flex: 1,
    backgroundColor: "#0f0f0f",
    alignItems: "center",
    justifyContent: "center",
  },
});
