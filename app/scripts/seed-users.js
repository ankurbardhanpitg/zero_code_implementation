const fs = require("fs/promises");
const path = require("path");

const DB_PATH = path.join(__dirname, "../data/users.json");

const seedUsers = [
  { name: "Aarav Sharma", email: "aarav.sharma@example.com" },
  { name: "Priya Patel", email: "priya.patel@example.com" },
  { name: "Rohan Mehta", email: "rohan.mehta@example.com" },
  { name: "Ananya Singh", email: "ananya.singh@example.com" },
  { name: "Vikram Reddy", email: "vikram.reddy@example.com" },
  { name: "Neha Gupta", email: "neha.gupta@example.com" },
  { name: "Arjun Nair", email: "arjun.nair@example.com" },
  { name: "Sneha Iyer", email: "sneha.iyer@example.com" },
  { name: "Karan Joshi", email: "karan.joshi@example.com" },
  { name: "Meera Das", email: "meera.das@example.com" },
];

async function seed() {
  const users = seedUsers.map((user, index) => ({
    id: index + 1,
    name: user.name,
    email: user.email,
    createdAt: new Date().toISOString(),
  }));

  await fs.mkdir(path.dirname(DB_PATH), { recursive: true });
  await fs.writeFile(DB_PATH, JSON.stringify(users, null, 2), "utf8");

  console.log(`Wrote ${users.length} users to ${DB_PATH}`);
}

seed().catch((error) => {
  console.error("Failed to seed users:", error);
  process.exit(1);
});
