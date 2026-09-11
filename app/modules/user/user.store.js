const fs = require("fs/promises");
const path = require("path");

const DB_PATH = path.join(__dirname, "../../data/users.json");

async function readUsers() {
  try {
    const data = await fs.readFile(DB_PATH, "utf8");
    return JSON.parse(data);
  } catch (error) {
    if (error.code === "ENOENT") {
      await writeUsers([]);
      return [];
    }
    throw error;
  }
}

async function writeUsers(users) {
  await fs.writeFile(DB_PATH, JSON.stringify(users, null, 2), "utf8");
}

async function getAll() {
  return readUsers();
}

function nextId(users) {
  return users.reduce((max, user) => Math.max(max, Number(user.id) || 0), 0) + 1;
}

function matchesId(user, id) {
  return Number(user.id) === Number(id);
}

async function getById(id) {
  const users = await readUsers();
  return users.find((user) => matchesId(user, id)) || null;
}

async function create(userData) {
  const users = await readUsers();
  const user = {
    id: nextId(users),
    name: userData.name,
    email: userData.email,
    createdAt: new Date().toISOString(),
  };

  users.push(user);
  await writeUsers(users);
  return user;
}

async function remove(id) {
  const users = await readUsers();
  const index = users.findIndex((user) => matchesId(user, id));

  if (index === -1) {
    return null;
  }

  const [deletedUser] = users.splice(index, 1);
  await writeUsers(users);
  return deletedUser;
}

module.exports = {
  getAll,
  getById,
  create,
  remove,
};
