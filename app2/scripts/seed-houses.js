const fs = require("fs/promises");
const path = require("path");

const DB_PATH = path.join(__dirname, "../data/houses.json");

const seedHouses = [
  { address: "12 MG Road", city: "Bengaluru", price: 18500000 },
  { address: "45 Marine Drive", city: "Mumbai", price: 42000000 },
  { address: "8 Park Street", city: "Kolkata", price: 9800000 },
  { address: "21 Connaught Place", city: "Delhi", price: 27500000 },
  { address: "3 Banjara Hills", city: "Hyderabad", price: 15200000 },
  { address: "77 Anna Salai", city: "Chennai", price: 11900000 },
  { address: "9 Koregaon Park", city: "Pune", price: 13400000 },
  { address: "16 Civil Lines", city: "Jaipur", price: 7600000 },
  { address: "4 Sector 17", city: "Chandigarh", price: 8900000 },
  { address: "31 Panampilly Nagar", city: "Kochi", price: 10200000 },
];

async function seed() {
  const houses = seedHouses.map((house, index) => ({
    id: index + 1,
    address: house.address,
    city: house.city,
    price: house.price,
    createdAt: new Date().toISOString(),
  }));

  await fs.mkdir(path.dirname(DB_PATH), { recursive: true });
  await fs.writeFile(DB_PATH, JSON.stringify(houses, null, 2), "utf8");

  console.log(`Wrote ${houses.length} houses to ${DB_PATH}`);
}

seed().catch((error) => {
  console.error("Failed to seed houses:", error);
  process.exit(1);
});
