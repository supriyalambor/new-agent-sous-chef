import { useState, useRef, useEffect } from "react";
import { createClient } from "@supabase/supabase-js";
import { useVoice } from "./hooks/useVoice";

const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
);

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const PLATFORMS = {
  licious:   { label: "Licious",   color: "#E8473F", emoji: "🥩", search: q => `https://www.licious.in/search?q=${encodeURIComponent(q)}` },
  instamart: { label: "Instamart", color: "#FC8019", emoji: "🛍️", search: q => `https://www.swiggy.com/instamart/search?query=${encodeURIComponent(q)}` },
  blinkit:   { label: "Blinkit",   color: "#F9C23C", emoji: "💛", search: q => `https://blinkit.com/s/?q=${encodeURIComponent(q)}` },
  mango:     { label: "Mango",     color: "#4CAF7D", emoji: "🏪", search: q => `https://www.google.com/search?q=mango+hypermarket+${encodeURIComponent(q)}` },
};

const TODAY = new Date();
const isVeg = TODAY.getDay() === 4;
const DAY_NAME = TODAY.toLocaleDateString("en-IN", { weekday: "long" });
const DATE_LABEL = TODAY.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "short" });
const DAY_OF_MONTH = TODAY.getDate();

function fmt(n) { return "₹" + Number(n || 0).toLocaleString("en-IN"); }

const QUICK_ACTIONS = [
  { emoji: "🍳", label: "Plan today", msg: `Plan today's meals` },
  { emoji: "📅", label: "Plan week", msg: "Plan my week Mon to Sun" },
  { emoji: "🛒", label: "Shopping list", msg: "Show me the shopping list" },
  { emoji: "💰", label: "Budget", msg: "How are we doing on budget this month?" },
  { emoji: "📧", label: "Email list", msg: "Email the grocery list to me and Vivek" },
];

export default function App() {
  const [messages, setMessages] = useState([{
    role: "assistant",
    content: `Hey Supriya! 👋 I'm your Sous Chef.\n\n${isVeg ? "🥦 Thursday — veg day today!" : `🥩 ${DAY_NAME} — non-veg day.`}\n\nI know your macros, your dishes, and your budget. What do you need?`,
    type: "text",
  }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [shoppingList, setShoppingList] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [totalMonth, setTotalMonth] = useState(0);
  const [activeTab, setActiveTab] = useState("chat");
  const [checkedItems, setCheckedItems] = useState({});
  const [newExp, setNewExp] = useState({ platform: "instamart", amount: "", note: "" });
  const bottomRef = useRef();
  const inputRef = useRef();

  const { listening, supported, startListening, stopListening } = useVoice((transcript) => {
    setInput(transcript);
    setTimeout(() => sendMessage(transcript), 300);
  });

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const [expRes, shopRes] = await Promise.all([
        fetch(`${API_URL}/api/expenses/`),
        fetch(`${API_URL}/api/meals/shopping`),
      ]);
      const expData = await expRes.json();
      const shopData = await shopRes.json();
      setExpenses(expData.expenses || []);
      setTotalMonth(expData.total || 0);
      if (shopData?.length) setShoppingList(shopData);
    } catch {}
  }

  async function sendMessage(text) {
    const msg = text || input;
    if (!msg.trim() || loading) return;
    setInput("");
    setLoading(true);

    const userMsg = { role: "user", content: msg, type: "text" };
    setMessages(prev => [...prev, userMsg, { role: "assistant", content: "", type: "typing" }]);

    try {
      const history = [...messages, userMsg]
        .filter(m => m.type !== "typing")
        .map(m => ({ role: m.role, content: m.content }));

      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
      });

      const data = await res.json();
      setMessages(prev => prev.filter(m => m.type !== "typing"));

      if (data.shopping_list?.length) {
        setShoppingList(data.shopping_list);
        setMessages(prev => [...prev, {
          role: "assistant", type: "plan",
          content: data.response,
          shoppingList: data.shopping_list,
        }]);
        setActiveTab("shop");
      } else {
        setMessages(prev => [...prev, { role: "assistant", type: "text", content: data.response }]);
      }
      await loadData();
    } catch (e) {
      setMessages(prev => [...prev.filter(m => m.type !== "typing"), {
        role: "assistant", type: "text", content: "Something went wrong. Try again!",
      }]);
    }
    setLoading(false);
  }

  async function addExpense() {
    if (!newExp.amount) return;
    await fetch(`${API_URL}/api/expenses/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform: newExp.platform, amount: parseInt(newExp.amount), note: newExp.note }),
    });
    setNewExp({ platform: "instamart", amount: "", note: "" });
    await loadData();
  }

  async function deleteExpense(id) {
    await fetch(`${API_URL}/api/expenses/${id}`, { method: "DELETE" });
    await loadData();
  }

  function renderText(text) {
    if (!text) return null;
    
    // Check if text contains a markdown table
    const lines = text.split("\n");
    const hasTable = lines.some(l => l.trim().startsWith("|") && l.includes("|"));
    
    if (hasTable) {
      const parts = [];
      let tableLines = [];
      let nonTableLines = [];
      
      for (const line of lines) {
        if (line.trim().startsWith("|")) {
          if (nonTableLines.length) {
            parts.push(<span key={parts.length} style={{whiteSpace:"pre-wrap"}}>{nonTableLines.join("\n")}</span>);
            nonTableLines = [];
          }
          tableLines.push(line);
        } else {
          if (tableLines.length) {
            parts.push(renderTable(tableLines, parts.length));
            tableLines = [];
          }
          nonTableLines.push(line);
        }
      }
      if (tableLines.length) parts.push(renderTable(tableLines, parts.length));
      if (nonTableLines.length) parts.push(<span key={parts.length} style={{whiteSpace:"pre-wrap"}}>{nonTableLines.join("\n")}</span>);
      return parts;
    }
    
    return (text || "").split(/(\*\*[^*]+\*\*)/).map((p, i) =>
      p.startsWith("**") ? <strong key={i} style={{ color: "#fff" }}>{p.slice(2, -2)}</strong> : p
    );
  }

  function renderTable(lines, key) {
    const rows = lines
      .filter(l => !l.match(/^\|[-| ]+\|$/))
      .map(l => l.split("|").filter((_, i, a) => i > 0 && i < a.length - 1).map(c => c.trim()));
    
    if (!rows.length) return null;
    const headers = rows[0];
    const body = rows.slice(1);
    
    return (
      <div key={key} style={{overflowX:"auto", margin:"8px 0"}}>
        <table style={{borderCollapse:"collapse", width:"100%", fontSize:12}}>
          <thead>
            <tr>{headers.map((h,i) => (
              <th key={i} style={{padding:"6px 10px", background:"#1A1A1A", color:"#4CAF7D", textAlign:"left", borderBottom:"1px solid #333", whiteSpace:"nowrap"}}>{h}</th>
            ))}</tr>
          </thead>
          <tbody>
            {body.map((row, i) => (
              <tr key={i} style={{borderBottom:"1px solid #1A1A1A"}}>
                {row.map((cell, j) => (
                  <td key={j} style={{padding:"5px 10px", color: cell.startsWith("~") || cell.includes("Total") ? "#F9C23C" : "#F0EBE3", whiteSpace:"nowrap", fontFamily: j > 1 ? "monospace" : "inherit"}}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  const projected = DAY_OF_MONTH > 0 ? Math.round((totalMonth / DAY_OF_MONTH) * 31) : 0;
  const budgetPct = Math.min((totalMonth / 38000) * 100, 100);

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#080808", color: "#F0EBE3", fontFamily: "'Inter',sans-serif", maxWidth: 480, margin: "0 auto" }}>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />

      {/* ── Header ── */}
      <div style={{ padding: "16px 20px 12px", background: "linear-gradient(180deg, #0F0F0F 0%, #080808 100%)", borderBottom: "1px solid #141414", flexShrink: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 22 }}>🍳</span>
              <div>
                <h1 style={{ margin: 0, fontSize: 17, fontWeight: 700, letterSpacing: -0.3 }}>Sous Chef</h1>
                <p style={{ margin: 0, fontSize: 10, color: "#555" }}>Supriya + Vivek · {DATE_LABEL}</p>
              </div>
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <span style={{
              background: isVeg ? "#0D1F12" : "#1A0A09",
              border: `1px solid ${isVeg ? "#1E3323" : "#3A1510"}`,
              color: isVeg ? "#4CAF7D" : "#E8473F",
              fontSize: 10, padding: "3px 10px", borderRadius: 20, fontWeight: 600,
            }}>{isVeg ? "🥦 Veg Day" : "🥩 Non-Veg"}</span>
            <p style={{ margin: "6px 0 0", fontSize: 17, fontWeight: 700, fontFamily: "monospace", color: totalMonth > 38000 ? "#E8473F" : "#F0EBE3" }}>{fmt(totalMonth)}</p>
            <p style={{ margin: "1px 0 0", fontSize: 9, color: "#444", fontFamily: "monospace" }}>proj. {fmt(projected)}</p>
          </div>
        </div>
        {/* Budget bar */}
        <div style={{ marginTop: 10, background: "#1A1A1A", borderRadius: 3, height: 3, overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${budgetPct}%`, background: budgetPct > 100 ? "#E8473F" : budgetPct > 80 ? "#F9C23C" : "#4CAF7D", borderRadius: 3, transition: "width 0.5s" }} />
        </div>
      </div>

      {/* ── Tabs ── */}
      <div style={{ display: "flex", borderBottom: "1px solid #141414", flexShrink: 0 }}>
        {[
          { id: "chat", label: "💬 Chat" },
          { id: "shop", label: `🛒 Shop${shoppingList.length ? ` (${shoppingList.length})` : ""}` },
          { id: "expenses", label: "📊 Spend" },
        ].map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
            flex: 1, padding: "10px 4px", border: "none", background: "transparent",
            color: activeTab === tab.id ? "#F0EBE3" : "#555",
            fontWeight: activeTab === tab.id ? 600 : 400,
            fontSize: 12, cursor: "pointer", fontFamily: "'Inter',sans-serif",
            borderBottom: `2px solid ${activeTab === tab.id ? "#4CAF7D" : "transparent"}`,
            transition: "all 0.2s",
          }}>{tab.label}</button>
        ))}
      </div>

      {/* ── Chat Tab ── */}
      {activeTab === "chat" && (
        <>
          <div style={{ flex: 1, overflowY: "auto", padding: "16px 16px 0" }}>
            {messages.map((msg, i) => {
              const isUser = msg.role === "user";
              if (msg.type === "typing") return (
                <div key={i} style={{ display: "flex", gap: 10, marginBottom: 16 }}>
                  <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#1A1A1A", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, flexShrink: 0 }}>🍳</div>
                  <div style={{ background: "#141414", borderRadius: "4px 16px 16px 16px", padding: "14px 18px", border: "1px solid #1E1E1E" }}>
                    <div style={{ display: "flex", gap: 4 }}>
                      {[0,1,2].map(j => (
                        <div key={j} style={{ width: 6, height: 6, borderRadius: "50%", background: "#555", animation: `bounce 1.2s ${j*0.2}s infinite` }} />
                      ))}
                    </div>
                    <style>{`@keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-6px)}}`}</style>
                  </div>
                </div>
              );

              return (
                <div key={i} style={{ display: "flex", gap: 10, marginBottom: 16, justifyContent: isUser ? "flex-end" : "flex-start", alignItems: "flex-end" }}>
                  {!isUser && <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#1A1A1A", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, flexShrink: 0 }}>🍳</div>}
                  <div style={{ maxWidth: "80%" }}>
                    <div style={{
                      background: isUser ? "linear-gradient(135deg, #1C3A1C, #1A2E1A)" : "#141414",
                      border: `1px solid ${isUser ? "#2A4A2A" : "#1E1E1E"}`,
                      borderRadius: isUser ? "16px 4px 16px 16px" : "4px 16px 16px 16px",
                      padding: "12px 16px", fontSize: 13, lineHeight: 1.7,
                      whiteSpace: "pre-wrap", color: "#F0EBE3",
                    }}>
                      {renderText(msg.content)}
                    </div>
                    {msg.type === "plan" && msg.shoppingList?.length > 0 && (
                      <button onClick={() => setActiveTab("shop")} style={{ marginTop: 8, padding: "6px 14px", background: "#F9C23C22", border: "1px solid #F9C23C55", borderRadius: 20, color: "#F9C23C", fontSize: 11, fontWeight: 600, cursor: "pointer", fontFamily: "'Inter',sans-serif" }}>
                        View shopping list →
                      </button>
                    )}
                  </div>
                  {isUser && <div style={{ width: 32, height: 32, borderRadius: "50%", background: "linear-gradient(135deg, #1C3A1C, #1A2E1A)", border: "1px solid #2A4A2A", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0 }}>S</div>}
                </div>
              );
            })}

            {/* Quick actions */}
            {messages.length <= 1 && (
              <div style={{ marginLeft: 42, marginBottom: 16 }}>
                <p style={{ margin: "0 0 10px", fontSize: 11, color: "#444" }}>Quick actions</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {QUICK_ACTIONS.map((a, i) => (
                    <button key={i} onClick={() => sendMessage(a.msg)} style={{ padding: "8px 14px", background: "#111", border: "1px solid #222", borderRadius: 20, color: "#888", fontSize: 12, cursor: "pointer", fontFamily: "'Inter',sans-serif", display: "flex", alignItems: "center", gap: 6 }}>
                      <span>{a.emoji}</span> {a.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Quick replies */}
          {messages.length > 2 && !loading && (
            <div style={{ padding: "8px 16px 0", display: "flex", gap: 6, overflowX: "auto", flexShrink: 0 }}>
              {QUICK_ACTIONS.slice(0, 4).map((a, i) => (
                <button key={i} onClick={() => sendMessage(a.msg)} style={{ flexShrink: 0, padding: "5px 12px", background: "#111", border: "1px solid #1E1E1E", borderRadius: 16, color: "#666", fontSize: 11, cursor: "pointer", fontFamily: "'Inter',sans-serif", marginBottom: 4 }}>
                  {a.emoji} {a.label}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div style={{ padding: "10px 16px 24px", borderTop: "1px solid #141414", flexShrink: 0 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center", background: "#111", border: `1px solid ${listening ? "#E8473F" : "#222"}`, borderRadius: 24, padding: "6px 6px 6px 16px", transition: "border-color 0.2s" }}>
              <input
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
                placeholder={listening ? "Listening..." : "Ask anything or tap 🎤"}
                style={{ flex: 1, background: "transparent", border: "none", color: listening ? "#E8473F" : "#F0EBE3", fontSize: 14, fontFamily: "'Inter',sans-serif", outline: "none" }}
              />
              {supported && (
                <button
                  onMouseDown={startListening}
                  onMouseUp={stopListening}
                  onTouchStart={startListening}
                  onTouchEnd={stopListening}
                  style={{
                    width: 38, height: 38, borderRadius: "50%", border: "none", cursor: "pointer",
                    background: listening ? "#E8473F" : "#1A1A1A",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 16, flexShrink: 0, transition: "all 0.2s",
                    boxShadow: listening ? "0 0 0 4px #E8473F33" : "none",
                  }}>
                  {listening ? "⏹" : "🎤"}
                </button>
              )}
              <button onClick={() => sendMessage()} disabled={loading || !input.trim()} style={{ width: 38, height: 38, borderRadius: "50%", border: "none", cursor: loading || !input.trim() ? "default" : "pointer", background: loading || !input.trim() ? "#1A1A1A" : "#4CAF7D", color: loading || !input.trim() ? "#333" : "#000", fontSize: 18, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, transition: "all 0.2s" }}>
                {loading ? "⟳" : "↑"}
              </button>
            </div>
          </div>
        </>
      )}

      {/* ── Shopping Tab ── */}
      {activeTab === "shop" && (
        <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
          {shoppingList.length === 0 ? (
            <div style={{ textAlign: "center", padding: "60px 20px" }}>
              <p style={{ fontSize: 48 }}>🛒</p>
              <p style={{ color: "#444", fontSize: 14 }}>No shopping list yet.</p>
              <button onClick={() => { setActiveTab("chat"); sendMessage("Plan my week"); }} style={{ marginTop: 12, padding: "10px 20px", background: "#4CAF7D", border: "none", borderRadius: 10, color: "#000", fontWeight: 700, cursor: "pointer", fontFamily: "'Inter',sans-serif" }}>
                Plan my week →
              </button>
            </div>
          ) : (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <p style={{ margin: 0, fontSize: 13, color: "#666" }}>{shoppingList.filter(i => !checkedItems[i.item]).length} items remaining</p>
                <p style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "#F9C23C", fontFamily: "monospace" }}>
                  {fmt(shoppingList.reduce((a, b) => a + Number(b.estimatedPrice || b.estimated_price || 0), 0))}
                </p>
              </div>
              {Object.entries(PLATFORMS).map(([pid, pconf]) => {
                const items = shoppingList.filter(i => (i.platform || "").toLowerCase() === pid);
                if (!items.length) return null;
                return (
                  <div key={pid} style={{ marginBottom: 16 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, padding: "6px 12px", background: pconf.color + "11", borderRadius: 8 }}>
                      <span style={{ fontSize: 16 }}>{pconf.emoji}</span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: pconf.color, letterSpacing: 1 }}>{pconf.label}</span>
                      <span style={{ marginLeft: "auto", fontSize: 12, color: pconf.color, fontFamily: "monospace" }}>
                        {fmt(items.reduce((a, b) => a + Number(b.estimatedPrice || b.estimated_price || 0), 0))}
                      </span>
                    </div>
                    {items.map((item, j) => {
                      const checked = !!checkedItems[item.item];
                      const price = Number(item.estimatedPrice || item.estimated_price || 0);
                      return (
                        <div key={j} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", marginBottom: 6, background: checked ? "#0D0D0D" : "#111", border: `1px solid ${checked ? "#141414" : "#1E1E1E"}`, borderRadius: 12, transition: "all 0.2s" }}>
                          <button onClick={() => setCheckedItems(c => ({ ...c, [item.item]: !c[item.item] }))} style={{ width: 22, height: 22, borderRadius: 6, flexShrink: 0, background: checked ? pconf.color : "transparent", border: `2px solid ${checked ? pconf.color : "#2A2A2A"}`, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            {checked && <span style={{ fontSize: 12, color: "#000" }}>✓</span>}
                          </button>
                          <div style={{ flex: 1, opacity: checked ? 0.4 : 1 }}>
                            <p style={{ margin: 0, fontSize: 13, fontWeight: 500, textDecoration: checked ? "line-through" : "none" }}>{item.item}</p>
                            <p style={{ margin: "2px 0 0", fontSize: 11, color: "#555" }}>{item.qty}</p>
                          </div>
                          <span style={{ fontSize: 12, fontWeight: 600, color: pconf.color, fontFamily: "monospace", flexShrink: 0 }}>{price > 0 ? fmt(price) : ""}</span>
                          <a href={pconf.search(item.item)} target="_blank" rel="noreferrer" style={{ padding: "4px 10px", background: pconf.color + "22", borderRadius: 8, color: pconf.color, fontSize: 11, textDecoration: "none", fontWeight: 600, flexShrink: 0 }}>Order →</a>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
              <button onClick={() => sendMessage("Email me the grocery list")} style={{ width: "100%", padding: 14, background: "#4CAF7D", border: "none", borderRadius: 12, color: "#000", fontWeight: 700, fontSize: 14, cursor: "pointer", fontFamily: "'Inter',sans-serif", marginTop: 8 }}>
                📧 Email to Vivek
              </button>
            </>
          )}
        </div>
      )}

      {/* ── Expenses Tab ── */}
      {activeTab === "expenses" && (
        <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
          {/* Summary */}
          <div style={{ background: "#111", border: "1px solid #1E1E1E", borderRadius: 16, padding: 16, marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
              <div>
                <p style={{ margin: 0, fontSize: 11, color: "#555" }}>Spent this month</p>
                <p style={{ margin: "4px 0 0", fontSize: 28, fontWeight: 700, fontFamily: "monospace", color: totalMonth > 38000 ? "#E8473F" : "#F0EBE3" }}>{fmt(totalMonth)}</p>
              </div>
              <div style={{ textAlign: "right" }}>
                <p style={{ margin: 0, fontSize: 11, color: "#555" }}>Projected</p>
                <p style={{ margin: "4px 0 0", fontSize: 28, fontWeight: 700, fontFamily: "monospace", color: projected > 38000 ? "#E8473F" : "#666" }}>{fmt(projected)}</p>
              </div>
            </div>
            <div style={{ background: "#1A1A1A", borderRadius: 3, height: 4 }}>
              <div style={{ height: "100%", width: `${budgetPct}%`, background: budgetPct > 100 ? "#E8473F" : budgetPct > 80 ? "#F9C23C" : "#4CAF7D", borderRadius: 3, transition: "width 0.5s" }} />
            </div>
            <p style={{ margin: "6px 0 0", fontSize: 10, color: "#444", fontFamily: "monospace" }}>Budget ₹38,000 · Day {DAY_OF_MONTH}/31</p>
          </div>

          {/* Platform breakdown */}
          <div style={{ display: "flex", gap: 8, marginBottom: 16, overflowX: "auto" }}>
            {Object.entries(PLATFORMS).map(([pid, pconf]) => {
              const amt = expenses.filter(e => e.platform === pid).reduce((a, b) => a + b.amount, 0);
              if (!amt) return null;
              return (
                <div key={pid} style={{ flexShrink: 0, background: pconf.color + "11", border: `1px solid ${pconf.color}33`, borderRadius: 12, padding: "10px 14px", minWidth: 80 }}>
                  <p style={{ margin: 0, fontSize: 18 }}>{pconf.emoji}</p>
                  <p style={{ margin: "4px 0 2px", fontSize: 14, fontWeight: 700, fontFamily: "monospace", color: pconf.color }}>{fmt(amt)}</p>
                  <p style={{ margin: 0, fontSize: 10, color: "#555" }}>{pconf.label}</p>
                </div>
              );
            })}
          </div>

          {/* Add expense */}
          <div style={{ background: "#111", border: "1px solid #1E1E1E", borderRadius: 12, padding: 14, marginBottom: 16 }}>
            <p style={{ margin: "0 0 10px", fontSize: 12, fontWeight: 600, color: "#888" }}>Log expense</p>
            <div style={{ display: "flex", gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
              {Object.entries(PLATFORMS).map(([pid, pconf]) => (
                <button key={pid} onClick={() => setNewExp(e => ({ ...e, platform: pid }))} style={{ padding: "6px 12px", borderRadius: 20, border: "none", cursor: "pointer", background: newExp.platform === pid ? pconf.color : "#1A1A1A", color: newExp.platform === pid ? "#000" : "#666", fontSize: 12, fontWeight: 600, fontFamily: "'Inter',sans-serif" }}>
                  {pconf.emoji} {pconf.label}
                </button>
              ))}
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <input type="number" placeholder="₹ Amount" value={newExp.amount} onChange={e => setNewExp(x => ({ ...x, amount: e.target.value }))} style={{ flex: 1, background: "#1A1A1A", border: "1px solid #222", borderRadius: 8, padding: "10px 12px", color: "#F0EBE3", fontSize: 13, fontFamily: "monospace", outline: "none" }} />
              <input placeholder="Note" value={newExp.note} onChange={e => setNewExp(x => ({ ...x, note: e.target.value }))} onKeyDown={e => e.key === "Enter" && addExpense()} style={{ flex: 1, background: "#1A1A1A", border: "1px solid #222", borderRadius: 8, padding: "10px 12px", color: "#F0EBE3", fontSize: 13, fontFamily: "'Inter',sans-serif", outline: "none" }} />
              <button onClick={addExpense} style={{ padding: "10px 16px", background: "#4CAF7D", border: "none", borderRadius: 8, color: "#000", fontWeight: 700, fontSize: 14, cursor: "pointer" }}>+</button>
            </div>
          </div>

          {/* Expense list */}
          {expenses.slice(0, 15).map(exp => {
            const p = PLATFORMS[exp.platform] || PLATFORMS.instamart;
            return (
              <div key={exp.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 14px", marginBottom: 8, background: "#0F0F0F", border: "1px solid #161616", borderRadius: 12 }}>
                <span style={{ fontSize: 20 }}>{p.emoji}</span>
                <div style={{ flex: 1 }}>
                  <p style={{ margin: 0, fontSize: 13, fontWeight: 500 }}>{exp.note || p.label}</p>
                  <p style={{ margin: "2px 0 0", fontSize: 11, color: "#444", fontFamily: "monospace" }}>
                    {new Date(exp.expense_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })} · {p.label}
                  </p>
                </div>
                <p style={{ margin: 0, fontSize: 15, fontWeight: 700, fontFamily: "monospace", color: p.color }}>{fmt(exp.amount)}</p>
                <button onClick={() => deleteExpense(exp.id)} style={{ background: "none", border: "none", color: "#2A2A2A", cursor: "pointer", fontSize: 16, padding: 4 }}>✕</button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
