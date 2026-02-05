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
  
  // Get the current origin and pathname to redirect back to the same page
  const redirectTo = `${window.location.origin}${window.location.pathname}`;
  
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: redirectTo,
      queryParams: {
        access_type: 'offline',
        prompt: 'consent',
      },
    },
  });
  
  if (error) {
    console.error("Google OAuth error:", error);
    throw new Error(error.message || "Google sign-in failed");
  }
  
  // OAuth will redirect, so we don't need to return anything
  // The redirect will happen automatically
};

const signInWithGitHub = async () => {
  checkSupabaseConfig();
  
  // Get the current origin and pathname to redirect back to the same page
  const redirectTo = `${window.location.origin}${window.location.pathname}`;
  
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "github",
    options: {
      redirectTo: redirectTo,
    },
  });
  
  if (error) {
    console.error("GitHub OAuth error:", error);
    throw new Error(error.message || "GitHub sign-in failed");
  }
  
  // OAuth will redirect, so we don't need to return anything
  // The redirect will happen automatically
};

const signInWithEmail = async (email, password) => {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) {
    // Provide more helpful error messages
    if (error.message.includes("Email not confirmed")) {
      throw new Error("Please check your email and click the confirmation link before signing in.");
    }
    throw new Error(error.message || "Invalid credentials");
  }
  return data.user;
};

const signUpWithEmail = async (email, password, name) => {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: name ? { data: { full_name: name } } : undefined,
  });
  if (error) throw new Error(error.message || "Sign up failed");
  
  // If email confirmation is required, user will need to check their email
  if (data.user && !data.session) {
    throw new Error("Please check your email to confirm your account before signing in.");
  }
  
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





