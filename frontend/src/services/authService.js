/**
 * Authentication Service (Supabase Auth)
 * Keeps the existing modal UI but replaces demo/mock auth with real Supabase Auth.
 */

import { supabase } from "./supabaseClient";

const checkSupabaseConfig = () => {
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "";
  const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "";
  
  if (!supabaseUrl || !supabaseAnonKey || supabaseUrl.includes("placeholder")) {
    throw new Error(
      "Supabase is not configured. Please set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in your .env file.\n\n" +
      "To find these values:\n" +
      "1. Go to https://app.supabase.com\n" +
      "2. Select your project\n" +
      "3. Click 'Settings' (gear icon) in the left sidebar\n" +
      "4. Click 'API' under Project Settings\n" +
      "5. Copy the 'Project URL' → this is your VITE_SUPABASE_URL\n" +
      "6. Copy the 'anon' or 'public' key → this is your VITE_SUPABASE_ANON_KEY\n\n" +
      "Create a .env file in the frontend/ directory with:\n" +
      "VITE_SUPABASE_URL=https://your-project-id.supabase.co\n" +
      "VITE_SUPABASE_ANON_KEY=your-anon-key-here"
    );
  }
};

const signInWithGoogle = async () => {
  checkSupabaseConfig();
  const { error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: window.location.origin,
    },
  });
  if (error) throw new Error(error.message || "Google sign-in failed");
};

const signInWithGitHub = async () => {
  checkSupabaseConfig();
  const { error } = await supabase.auth.signInWithOAuth({
    provider: "github",
    options: {
      redirectTo: window.location.origin,
    },
  });
  if (error) throw new Error(error.message || "GitHub sign-in failed");
};

const signInWithEmail = async (email, password) => {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) throw new Error(error.message || "Invalid credentials");
  return data.user;
};

const signUpWithEmail = async (email, password, name) => {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: name ? { data: { full_name: name } } : undefined,
  });
  if (error) throw new Error(error.message || "Sign up failed");
  return data.user;
};

const signOut = async () => {
  const { error } = await supabase.auth.signOut();
  if (error) throw new Error(error.message || "Sign out failed");
};

const authService = {
  signInWithGoogle,
  signInWithGitHub,
  signInWithEmail,
  signUpWithEmail,
  signOut,
};

export default authService;





