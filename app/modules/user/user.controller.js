const userStore = require("./user.store");

async function addUser(req, res) {
  const { name, email } = req.body || {};

  if (!name || !email) {
    return res.status(400).json({
      error: "name and email are required",
    });
  }

  const user = await userStore.create({ name, email });
  return res.status(201).json(user);
}

async function fetchUsers(_req, res) {
  const users = await userStore.getAll();
  return res.json(users);
}

async function fetchUserById(req, res) {
  const user = await userStore.getById(req.params.id);

  if (!user) {
    return res.status(404).json({ error: "user not found" });
  }

  return res.json(user);
}

async function deleteUser(req, res) {
  const deletedUser = await userStore.remove(req.params.id);

  if (!deletedUser) {
    return res.status(404).json({ error: "user not found" });
  }

  return res.json({
    message: "user deleted",
    user: deletedUser,
  });
}

module.exports = {
  addUser,
  fetchUsers,
  fetchUserById,
  deleteUser,
};
