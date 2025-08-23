"use client";

import React from "react";
import { Toaster } from "react-hot-toast";

const ToasterProvider: React.FC = () => {
  return <Toaster position="top-right" toastOptions={{ duration: 3500 }} />;
};

export default ToasterProvider;


